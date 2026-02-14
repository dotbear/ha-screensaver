ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python and pip
# This is much faster than installing Rust toolchain (30 seconds vs 10 minutes)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-pillow \
    bash

# Create app directory
WORKDIR /app

# Copy requirements first (for better Docker layer caching)
# If requirements don't change, this layer is cached on rebuilds
COPY requirements.txt .

# Install Python dependencies
# The --no-cache-dir flag prevents pip from caching, saving space
# The --break-system-packages flag is needed for PEP 668 compliance in Alpine
# This is safe in a Docker container since it's an isolated environment
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code
COPY app.py .
COPY static ./static

# Create photos directory
RUN mkdir -p /app/photos

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

# Expose port (documentation only, actual port mapping in config.yaml)
EXPOSE 8080

# Run the application
CMD [ "/run.sh" ]
