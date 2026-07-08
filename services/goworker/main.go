package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"strings"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	oteltrace "go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("goworker-svc")

func initTracer() {
	ctx := context.Background()

	otlpEndpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if otlpEndpoint == "" {
		otlpEndpoint = "http://otel-collector:4318"
	}
	otlpEndpoint = strings.TrimPrefix(otlpEndpoint, "http://")
	otlpEndpoint = strings.TrimPrefix(otlpEndpoint, "https://")
	otlpEndpoint = strings.TrimSuffix(otlpEndpoint, "/v1/traces")

	exporter, err := otlptracehttp.New(ctx,
		otlptracehttp.WithInsecure(),
		otlptracehttp.WithEndpoint(otlpEndpoint),
	)
	if err != nil {
		log.Fatalf("failed to create exporter: %v", err)
	}

	res := resource.NewWithAttributes(
		semconv.SchemaURL,
		semconv.ServiceName("goworker-svc"),
		semconv.ServiceVersion("1.0.0"),
	)

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))
}

func logWithTrace(ctx context.Context, msg string) {
	span := oteltrace.SpanFromContext(ctx)
	if span != nil && span.SpanContext().HasTraceID() {
		tid := span.SpanContext().TraceID().String()
		sid := span.SpanContext().SpanID().String()
		log.Printf("trace_id=%s span_id=%s %s", tid, sid, msg)
	} else {
		log.Printf("trace_id= span_id= %s", msg)
	}
}

func main() {
	initTracer()

	mux := http.NewServeMux()
	mux.HandleFunc("/work", func(w http.ResponseWriter, r *http.Request) {
		ctx, span := tracer.Start(r.Context(), "do_work")
		span.SetAttributes(
			attribute.String("slo_tier", "batch"),
			attribute.String("service.version", "1.0.0"),
			attribute.String("work_type", "compute"),
		)
		defer span.End()

		logWithTrace(ctx, "Starting work")
		time.Sleep(time.Duration(rand.Intn(50)) * time.Millisecond)

		result := map[string]string{
			"service": "goworker-svc",
			"status":  "completed",
			"result":  "work_done",
		}
		span.SetAttributes(attribute.String("result", "work_done"))
		span.AddEvent("work_completed")
		logWithTrace(ctx, fmt.Sprintf("Work completed: %s", result["status"]))

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
	})

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	handler := otelhttp.NewHandler(mux, "goworker-svc-handler")

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("goworker-svc on :%s", port)
	http.ListenAndServe(":"+port, handler)
}
