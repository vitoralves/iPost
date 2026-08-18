# syntax=docker/dockerfile:1
FROM public.ecr.aws/lambda/python:3.12

COPY packages/ipost /tmp/ipost
RUN pip install --no-cache-dir /tmp/ipost && rm -rf /tmp/ipost

CMD ["ipost.agents.lambda_handler.lambda_handler"]
