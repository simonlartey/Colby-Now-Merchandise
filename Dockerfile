FROM python:3.13-slim
RUN useradd -m mulemart
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN chmod +x boot.sh
RUN chown -R mulemart:mulemart .
USER mulemart
CMD ["./boot.sh"]