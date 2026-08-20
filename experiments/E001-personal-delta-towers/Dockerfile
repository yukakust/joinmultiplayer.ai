FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/work/src

WORKDIR /work

COPY requirements-cpu.txt /tmp/requirements-cpu.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements-cpu.txt

COPY . /work

CMD ["python", "-m", "e001.run", "--config", "configs/pilot.json"]
