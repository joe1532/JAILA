# 🚀 GRAPH RETRIEVER - INSTALLATION & QUICK START

## 📦 **INSTALLATION**

### Requirements
```bash
pip install openai python-dotenv
```

### Environment Setup
```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Or create .env file
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### Package Usage
```python
# Add to Python path
import sys
sys.path.append('path/to/graph_retriever')

# Import modules
from graph_retriever import GraphBuilder, GraphRetriever
```

---

## ⚡ **QUICK START**

### 1. Build Your First Graph

```python
from graph_retriever import GraphBuilder

# Sample paragraph data
paragraphs = [
    {
        'id': '§15P',
        'content': 'Ved opgørelsen af den skattepligtige indkomst kan fradrages udgifter til renovering af boliger. Dette gælder dog kun, såfremt betingelserne i §15O er opfyldt.',
        'metadata': {'chapter': 'Kapitel 3', 'title': 'Renoveringsfradrag'}
    },
    {
        'id': '§15O',
        'content': 'Renovering skal være udført af en autoriseret håndværker.',
        'metadata': {'chapter': 'Kapitel 3', 'title': 'Betingelser'}
    }
]

# Build graph
builder = GraphBuilder(verbose=True)
graph = builder.build_graph("test_law", paragraphs)

print(f"Graph built: {graph.get_statistics()}")
```

### 2. Use Graph for Enhanced Retrieval

```python
from graph_retriever import GraphRetriever

# Create retriever
retriever = GraphRetriever()
retriever.graphs["test_law"] = graph

# Sample base search results
base_results = [
    {'paragraph': '§15P', 'text': 'renovering content...', 'score': 0.8}
]

# Get enhanced results
enhanced = retriever.get_graph_enhanced_results(
    query_terms=['renovering'],
    base_results=base_results,
    law_name="test_law"
)

print(f"Enhanced from {len(base_results)} to {len(enhanced)} results")
```

### 3. Integration with JAILA (Optional)

```python
# Requires JAILA system running
from graph_retriever.integration import get_enhanced_search_engine

search_engine = get_enhanced_search_engine()
results = search_engine.search("renovering §15P", enable_graph_enhancement=True)
```

---

## 🧪 **TESTING**

```bash
# Run demo
cd graph_retriever
python demo_graph_retriever.py

# Test specific module
python -c "from graph_retriever import GraphBuilder; print('✅ Import successful')"
```

---

## 📋 **COST EXAMPLE**

Building a graph for Ligningsloven (701 paragraphs):
- **Input tokens:** ~140,000
- **Output tokens:** ~105,000  
- **Cost:** ~$0.38 USD (~3 DKK)
- **One-time cost** - graph is reusable

---

## 🔧 **TROUBLESHOOTING**

**Import Error:**
```python
# Make sure path is correct
import sys
sys.path.append('/path/to/Weaviate')  # Parent directory
from graph_retriever import GraphBuilder
```

**OpenAI Error:**
```bash
# Check API key
echo $OPENAI_API_KEY

# Or in Python
import os
print(os.getenv("OPENAI_API_KEY"))
```

**Weaviate Connection (for JAILA integration):**
```bash
# Check if Weaviate is running
curl http://localhost:8080/v1/.well-known/live
```

---

## ✅ **NEXT STEPS**

1. **Test basic functionality** with demo
2. **Build graph** for your legal documents
3. **Integrate** with your search system
4. **Monitor performance** and costs

**Happy graph building!** 🎉 