runtime: python310
entrypoint: gunicorn -b :$PORT --timeout 60 --workers 2 main:app

env_variables:
  GATEWAY_URL: ${GATEWAY_URL}
