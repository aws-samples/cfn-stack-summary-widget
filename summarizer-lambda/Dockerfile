FROM python:3.9-buster

RUN apt-get update \
    && apt-get install -qy unzip zip

ARG OUTPUT_DIR=/asset-output
ARG BUILD_DIR=/build
ARG INPUT_DIR=/asset-input
RUN mkdir "$OUTPUT_DIR" "$BUILD_DIR"
WORKDIR $INPUT_DIR
RUN ls -al
COPY Pipfile Pipfile.lock /
RUN python -m venv /tmp/.venv && \
    /tmp/.venv/bin/python -m pip install -qU pip~=21.3.1 && \
    /tmp/.venv/bin/python -m pip install -qU pipenv~=2022.8.24 && \
    /tmp/.venv/bin/pipenv check && \
    /tmp/.venv/bin/pipenv requirements > "$BUILD_DIR/requirements.txt" && \
    /tmp/.venv/bin/python -m pip install -q -r "$BUILD_DIR/requirements.txt" --no-compile --target "$BUILD_DIR"
COPY *.py *.j2 *.md $BUILD_DIR/
COPY resource_types/ $BUILD_DIR/resource_types/
WORKDIR $BUILD_DIR
RUN zip -qr "/root/lambda.zip" *
