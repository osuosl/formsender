FROM python:3.10-alpine

COPY conf.py.dist /formsender/conf.py
COPY requirements.txt /formsender/requirements.txt
WORKDIR /formsender
RUN pip install -r requirements.txt
COPY . /formsender
ENTRYPOINT ["python3"]
CMD ["request_handler.py"]
EXPOSE 5000
