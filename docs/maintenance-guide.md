# SaaS Webhooks Catalog maintenance guide

Check the vendor source and verification notes before implementing an event. Snapshot dates describe the input data, not the last site rebuild. Unknown auth, retry or payload details must stay unknown until verified.

## Installation and compatibility

Follow the repository README for the supported install method and runtime. Pin the version used in a reproducible example. Keep credentials in your client configuration, outside shared fixtures.

## Verify a change

Record the package or snapshot version, exact input, observation time and actual output. Check a materially different input and a valid neighboring case. Treat expected output as a fixture, not a live measurement.
