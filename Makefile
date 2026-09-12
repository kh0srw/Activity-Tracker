.PHONY: build test vet check install

build:
	go build -trimpath -ldflags="-s -w" -o activity-tracker ./cmd/activity-tracker

test:
	go test ./...

vet:
	go vet ./...

check: test vet build

install: build
	./activity-tracker install
