# Explain Plan Viz Tool

This is a Flask-based webapp that converts Greenplum and HDB explain [analyze] plan text into a Graphviz dot representation then to an image of the resulting graph.

- Colors represent slice grouping
- Edge arrows are weighted proportionally (8px max), baselined on the maxmimum rows
- For large plans, mileage will vary
