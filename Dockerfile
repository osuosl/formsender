FROM osuosl/python_webapp

EXPOSE 5000
COPY . /opt/formsender
WORKDIR /opt/formsender
RUN pip install -r requirements.txt

CMD make run
