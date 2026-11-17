# Knowledge base for the farming assistant

The chatbot answers only from the documents in this folder. Each `.md` file is
split into passages, and the passages closest to the farmer's question are
given to the language model as its only source.

These files are a small starter set written for the project. They summarise
widely published guidance, but scheme amounts, dates and rules change. Before
relying on them, check each one against the official source named at the top
of the file, or replace them with documents from your state agriculture
department, ICAR or your Krishi Vigyan Kendra.

To add or change documents:

1. Put `.md` or `.txt` files in this folder (this README is ignored).
2. Start each file with a `# Title` line and use `## Section` headings.
3. Run `python -m kisan.chatbot.ingest` to rebuild the search index.
