"""
Captcha backends: Cloudflare Turnstile, self-hosted ALTCHA, Google reCAPTCHA.
See docs/source/usage.rst and docs/source/form_setup.rst.
"""

import collections
import logging
import time

import altcha
import requests

import conf

logger = logging.getLogger('formsender')

TURNSTILE_VERIFY_URL = \
    'https://challenges.cloudflare.com/turnstile/v0/siteverify'
RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
# Seconds to wait for a hosted verifier before giving up
VERIFY_TIMEOUT = 10
# Key derivation functions that work with a plain iteration count and no
# extra package. Anything else the library silently downgrades to plain SHA.
ALTCHA_ALGORITHMS = ('PBKDF2/SHA-256', 'PBKDF2/SHA-384', 'PBKDF2/SHA-512',
                     'SHA-256', 'SHA-384', 'SHA-512')

Provider = collections.namedtuple('Provider', 'name field secret verify')

# Reused so repeated verifications skip the TLS handshake
session = requests.Session()


def _setting(name, default=None):
    """Read an optional conf.py setting, treating None as unset"""
    value = getattr(conf, name, None)
    return default if value is None else value


def _siteverify(url, secret, token, remote_ip):
    """POST a token to a siteverify endpoint; None if the call failed"""
    data = {'secret': secret, 'response': token}
    if remote_ip:
        data['remoteip'] = remote_ip
    try:
        response = session.post(url, data=data, timeout=VERIFY_TIMEOUT)
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.error('formsender: captcha verification request to %s failed: '
                     '%s', url, error)
        return None
    if not isinstance(result, dict):
        logger.error('formsender: captcha verifier %s returned %s, not an '
                     'object', url, type(result).__name__)
        return None
    return result


def allowed_hostnames():
    """Parsed CAPTCHA_ALLOWED_HOSTNAMES, or None when the check is off"""
    raw = _setting('CAPTCHA_ALLOWED_HOSTNAMES')
    if raw is None:
        return None
    hosts = {host.strip().lower() for host in raw.split(',') if host.strip()}
    if not hosts:
        # Failing open here would silently disable the check after a typo
        raise RuntimeError('CAPTCHA_ALLOWED_HOSTNAMES is set but names no '
                           'hostnames; unset it to disable the check')
    return hosts


def _hostname_allowed(result):
    """Refuse a token a hosted provider says was solved on another site"""
    allowed = allowed_hostnames()
    if allowed is None:
        return True
    hostname = (result.get('hostname') or '').lower()
    if hostname in allowed:
        return True
    logger.warning('formsender: captcha solved on %r, which is not in '
                   'CAPTCHA_ALLOWED_HOSTNAMES', hostname)
    return False


def _hosted_response_is_good(provider, result):
    """Shared success handling for the two hosted verifiers"""
    if not result or not result.get('success'):
        logger.warning('formsender: %s rejected the response: %s', provider,
                       (result or {}).get('error-codes')
                       or 'no response from verifier')
        return False
    # reCAPTCHA fails open once its quota is spent: success is true, an error
    # code is attached and the score is a fixed 0.9. Refuse to trust that.
    codes = result.get('error-codes')
    if codes:
        logger.error('formsender: %s reported %s alongside success, so the '
                     'verdict is not trustworthy', provider, codes)
        return False
    return _hostname_allowed(result)


def verify_turnstile(token, remote_ip, controller):
    """Verify a Cloudflare Turnstile response token"""
    result = _siteverify(TURNSTILE_VERIFY_URL, conf.TURNSTILE_SECRET, token,
                         remote_ip)
    return _hosted_response_is_good('turnstile', result)


def verify_recaptcha(token, remote_ip, controller):
    """Verify a reCAPTCHA token, applying the score that v3 keys return"""
    result = _siteverify(RECAPTCHA_VERIFY_URL, conf.RECAPTCHA_SECRET, token,
                         remote_ip)
    if not _hosted_response_is_good('recaptcha', result):
        return False
    score = result.get('score')
    if score is None:
        return True
    try:
        if float(score) < float(_setting('RECAPTCHA_MIN_SCORE', 0.5)):
            logger.warning('formsender: recaptcha score %s is below '
                           'RECAPTCHA_MIN_SCORE', score)
            return False
    except (TypeError, ValueError) as error:
        logger.error('formsender: recaptcha score %r could not be compared '
                     'with RECAPTCHA_MIN_SCORE: %s', score, error)
        return False
    return True


def verify_altcha(payload, remote_ip, controller):
    """Verify an ALTCHA proof of work, then refuse a reused challenge"""
    try:
        parsed = altcha.Payload.from_base64(payload)
        result = altcha.verify_solution(parsed, conf.ALTCHA_HMAC_KEY)
    except Exception as error:
        # Every field here is attacker supplied, so a decode or type error is
        # a rejected submission rather than a server error.
        logger.warning('formsender: altcha payload was not usable: %s: %s',
                       type(error).__name__, error)
        return False
    if not result.verified:
        logger.warning('formsender: altcha rejected the solution: expired=%s '
                       'invalid_signature=%s invalid_solution=%s error=%s',
                       result.expired, result.invalid_signature,
                       result.invalid_solution, result.error)
        return False
    params = parsed.challenge.parameters
    # /altcha always sets an expiry, so a challenge without one is not ours
    if not params.expires_at:
        logger.warning('formsender: altcha challenge has no expiry')
        return False
    if controller.is_replayed_challenge(params.nonce, params.expires_at):
        logger.warning('formsender: altcha challenge %s was already used',
                       params.nonce)
        return False
    return True


def altcha_algorithm():
    """The configured ALTCHA key derivation function, validated"""
    algorithm = _setting('ALTCHA_ALGORITHM', 'PBKDF2/SHA-256')
    if algorithm not in ALTCHA_ALGORITHMS:
        raise RuntimeError('ALTCHA_ALGORITHM %r is not supported; use one of '
                           '%s' % (algorithm, ', '.join(ALTCHA_ALGORITHMS)))
    return algorithm


def create_altcha_challenge():
    """Issue a signed, expiring challenge for the ALTCHA widget"""
    expires_at = int(time.time()) + int(_setting('ALTCHA_EXPIRES', 600))
    challenge = altcha.create_challenge(altcha_algorithm(),
                                        int(_setting('ALTCHA_COST', 5000)),
                                        expires_at=expires_at,
                                        hmac_secret=conf.ALTCHA_HMAC_KEY)
    return challenge.to_dict()


# Checked in the order a submission is inspected
PROVIDERS = (
    Provider('turnstile', 'cf-turnstile-response', 'TURNSTILE_SECRET',
             verify_turnstile),
    Provider('altcha', 'altcha', 'ALTCHA_HMAC_KEY', verify_altcha),
    Provider('recaptcha', 'g-recaptcha-response', 'RECAPTCHA_SECRET',
             verify_recaptcha),
)

# Form fields carrying a captcha response; never part of the ticket body
FIELDS = tuple(provider.field for provider in PROVIDERS)


def configured_providers():
    """Names of the providers whose secret is set"""
    return [provider.name for provider in PROVIDERS
            if _setting(provider.secret)]


def check_configuration():
    """Validate the captcha settings at startup so typos fail fast"""
    providers = configured_providers()
    if not providers:
        raise RuntimeError('No captcha provider is configured; set at least '
                           'one of TURNSTILE_SECRET, ALTCHA_HMAC_KEY or '
                           'RECAPTCHA_SECRET')
    allowed_hostnames()
    if 'altcha' in providers:
        altcha_algorithm()
    return providers


def is_valid_captcha(request, controller):
    """Verify the submission's captcha; returns (ok, provider name or None)"""
    for provider in PROVIDERS:
        token = request.form.get(provider.field)
        if not token:
            continue
        if not _setting(provider.secret):
            logger.warning('formsender: form posted %s but %s is not '
                           'configured', provider.field, provider.secret)
            return False, provider.name
        valid = provider.verify(token, request.remote_addr, controller)
        return bool(valid), provider.name
    logger.warning('formsender: submission carried no captcha response')
    return False, None
