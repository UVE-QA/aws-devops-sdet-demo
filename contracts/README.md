# contracts/

The messages the services exchange, as JSON Schema — the one place both ends
of a queue agree on the shape (ADR-0098). The api builds `item.created` and
consumes `item.processed`; the worker consumes `item.created` and builds
`item.processed`. Neither imports the other's code, and neither validates
against these files at runtime: the parsers are strict by hand. What the
schemas do is hold the two ends still in `tests/unit/test_contracts.py`,
where every builder is validated against its schema and every parser is run
over the schema's own examples and counter-examples. A producer that changes
a meaning bumps `version`; a consumer that needs a field it does not find
refuses the message as poison.
