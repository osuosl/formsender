FROM osuosl/python_webapp

EXPOSE 5000
COPY requirements.txt /root/
RUN pip install --upgrade pip && pip install -r /root/requirements.txt

CMD make run
