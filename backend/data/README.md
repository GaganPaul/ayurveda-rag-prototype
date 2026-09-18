# Ayurveda RAG Prototype — Curated TXT Knowledge Base

This folder contains a small, curated starter knowledge base for the Render prototype.

## Structure

- classical/ — foundational Ayurvedic concepts
- medicinal_plants/ — conservative educational summaries of selected plants
- research/ — evidence literacy and CCRAS research context
- safety/ — safety, WHO benchmarks, and pharmacovigilance

## Important

These files are intentionally written as educational RAG data rather than medical treatment instructions.

For the WHO benchmark and pharmacovigilance documents, the files contain summaries and source metadata rather than reproductions of the copyrighted PDFs. Keep the original PDFs separately if your ingestion pipeline supports them.

For medicinal-plant claims, add the user's downloaded research PDFs to the knowledge base when the project supports PDF ingestion. The TXT files avoid making unsupported condition-specific claims.

## Recommended ingestion order

1. safety/
2. research/
3. classical/
4. medicinal_plants/

This gives the chatbot safety and evidence context before plant-specific information.

## Sources

WHO — WHO benchmarks for the practice of Ayurveda (2022):
https://www.who.int/publications/i/item/9789240042674

WHO — Pharmacovigilance for traditional medicine products: Why and how?:
https://www.who.int/publications/i/item/10665-259854

WHO — Traditional medicine Q&A:
https://www.who.int/news-room/questions-and-answers/item/traditional-medicine

WHO — International standard terminologies on Ayurveda:
https://www.who.int/publications/i/item/9789240064935

CCRAS — Clinical Research:
https://ccras.nic.in/documents/clinical-research/

## Testing prompts

- What is Ayurveda?
- What are Vata, Pitta and Kapha?
- What is Dinacharya?
- What is the traditional use of turmeric?
- What does modern research say about ashwagandha?
- Are herbal medicines always safe?
- Can I stop my prescribed medicine and use Ayurveda instead?
- I have severe chest pain. What should I do?
- What evidence is needed before saying an Ayurvedic treatment works?
- XYZFAKEHERB123: explain this herb.  (Expected behavior: say that it is not found in the knowledge base rather than hallucinating.)
