FROM golang:latest AS builder
WORKDIR /app
RUN go mod init goworker-svc
COPY main.go .
RUN go mod tidy
RUN CGO_ENABLED=0 go build -o goworker .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=builder /app/goworker /goworker
CMD ["/goworker"]
