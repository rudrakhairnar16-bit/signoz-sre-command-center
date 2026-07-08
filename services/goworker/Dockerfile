FROM golang:1.26-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY main.go .
RUN CGO_ENABLED=0 go build -o goworker .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=builder /app/goworker /goworker
CMD ["/goworker"]
