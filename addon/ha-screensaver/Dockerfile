ARG BUILD_FROM
FROM $BUILD_FROM AS builder

# Install build dependencies
RUN apk add --no-cache \
    cargo \
    rust \
    musl-dev

# Create app directory
WORKDIR /app

# Copy source code
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY static ./static

# Build the application
RUN cargo build --release

# Final stage
FROM $BUILD_FROM

# Install runtime dependencies
RUN apk add --no-cache libgcc

# Copy the binary from builder
COPY --from=builder /app/target/release/ha-screensaver /usr/local/bin/ha-screensaver
COPY --from=builder /app/static /app/static

# Create photos directory
RUN mkdir -p /app/photos

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

WORKDIR /app

CMD [ "/run.sh" ]
