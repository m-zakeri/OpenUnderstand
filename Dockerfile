FROM python:3.11

WORKDIR /app

COPY . .

RUN pip install pytest pytest-cov hypothesis flake8

CMD ["python", "-m", "pytest", "test_utilities.py"]
