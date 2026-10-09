FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup --system netbox-tools \
    && adduser --system --ingroup netbox-tools --home /nonexistent --no-create-home netbox-tools

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --requirement /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY --chmod=755 netbox_*.py /usr/local/bin/

USER netbox-tools

CMD ["netbox_list_tenants.py"]
