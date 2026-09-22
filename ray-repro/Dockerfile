# Dockerfile for Ray #47439 reproduction
# Base image ships ray 2.10.0 (core, tune, train). The reproduction models the
# nested placement-group request directly with the core PG API — no extra
# packages needed (xgboost-ray itself is not required to exhibit the deadlock;
# the issue is in PG scheduling, not in the trainer).
FROM rayproject/ray:2.10.0

WORKDIR /app

COPY ray-repro/reproduce_47439.py /app/reproduce_47439.py

# Default command: run the reproduction script
CMD ["python", "reproduce_47439.py"]
