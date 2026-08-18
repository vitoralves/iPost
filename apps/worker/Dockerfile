# syntax=docker/dockerfile:1
FROM public.ecr.aws/lambda/python:3.12

RUN dnf install -y tar xz \
    && curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp \
    && install -m 0755 /tmp/ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg \
    && rm -rf /tmp/ffmpeg* \
    && dnf clean all

COPY packages/ipost /tmp/ipost
RUN pip install --no-cache-dir /tmp/ipost && rm -rf /tmp/ipost

CMD ["ipost.agents.lambda_handler.lambda_handler"]
