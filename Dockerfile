FROM python:3.10-alpine

COPY conf.py.dist /formsender/conf.py
COPY requirements.txt /formsender/requirements.txt
WORKDIR /formsender
RUN pip  --no-cache-dir install -r requirements.txt
COPY . /formsender
ENTRYPOINT ["/formsender/entrypoint.sh"]
EXPOSE 5000
