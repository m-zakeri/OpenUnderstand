# Reproducible test environment (bonus challenge).
# Builds an image that runs linting, the isolated unit suite, and the coverage
# quality gates exactly as CI does.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt requirements-dev.txt ./
RUN python -m pip install --upgrade pip && \
    pip install -r requirements-dev.txt

# Copy the project.
COPY . .

# Default command: lint + tests + coverage gates.
CMD ["bash", "-lc", "\
    ruff check tests && \
    pytest tests \
      --cov=openunderstand.oudb.api \
      --cov=openunderstand.oudb.models \
      --cov-branch \
      --cov-report=term-missing \
      --cov-report=json && \
    python -c \"import json,sys; t=json.load(open('coverage.json'))['totals']; \
line=t['percent_covered']; nb=t.get('num_branches',0); cb=t.get('covered_branches',0); \
branch=(cb/nb*100) if nb else 100.0; \
print(f'line={line:.2f}% branch={branch:.2f}%'); \
sys.exit(0 if line>=80 and branch>=70 else 1)\" \
    "]
