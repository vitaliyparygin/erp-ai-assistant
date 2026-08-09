from langchain_core.prompts import ChatPromptTemplate

from app.rag.prompts import (
    QUERY_REWRITE_TEMPLATE,
    RETRIEVAL_ANALYSIS_TEMPLATE,
    RESEARCH_TEMPLATE,
    SUMMARIZER_TEMPLATE,
    CITATION_EXTRACTION_TEMPLATE,
    CONVERSATION_SUMMARY_TEMPLATE,
)
from langchain_core.messages import HumanMessage
from app.rag import prompts


def test_all_prompts_are_chat_prompt_templates():
    prompt_objects = [
        prompts.QUERY_REWRITE_TEMPLATE,
        prompts.RETRIEVAL_ANALYSIS_TEMPLATE,
        prompts.RESEARCH_TEMPLATE,
        prompts.SUMMARIZER_TEMPLATE,
        prompts.CITATION_EXTRACTION_TEMPLATE,
        prompts.CONVERSATION_SUMMARY_TEMPLATE,
    ]

    for prompt in prompt_objects:
        assert isinstance(prompt, ChatPromptTemplate)


def test_conversation_summary_prompt():
    prompt = CONVERSATION_SUMMARY_TEMPLATE.invoke(
        {
            "conversation": "history",
        }
    )

    assert "history" in prompt.to_string()


def test_citation_prompt():
    prompt = CITATION_EXTRACTION_TEMPLATE.invoke(
        {
            "answer": "answer",
            "chunks": "chunk1",
        }
    )

    text = prompt.to_string()

    assert "answer" in text
    assert "chunk1" in text


def test_summarizer_prompt():
    prompt = SUMMARIZER_TEMPLATE.invoke(
        {
            "history": [
                HumanMessage(content="hi"),
            ],
            "query": "question",
            "context": "context",
        }
    )

    text = prompt.to_string()

    assert "question" in text
    assert "context" in text


def test_research_prompt():
    prompt = RESEARCH_TEMPLATE.invoke(
        {
            "history": [
                HumanMessage(content="hello"),
            ],
            "query": "invoice",
            "context": "ctx",
            "research_notes": "notes",
        }
    )

    text = prompt.to_string()

    assert "invoice" in text
    assert "notes" in text


def test_retrieval_analysis_prompt():
    prompt = RETRIEVAL_ANALYSIS_TEMPLATE.invoke(
        {
            "query": "invoice",
            "context": "invoice text",
        }
    )

    text = prompt.to_string()

    assert "invoice" in text
    assert "invoice text" in text


def test_query_rewrite_prompt():
    prompt = QUERY_REWRITE_TEMPLATE.invoke(
        {
            "conversation_context": "ctx",
            "query": "hello",
        }
    )

    text = prompt.to_string()

    assert "ctx" in text
    assert "hello" in text


def test_query_rewrite_format():
    messages = QUERY_REWRITE_TEMPLATE.format_messages(
        conversation_context="ctx",
        query="invoice",
    )

    assert len(messages) == 2


def test_query_rewrite_variables():
    assert set(QUERY_REWRITE_TEMPLATE.input_variables) == {
        "conversation_context",
        "query",
    }


def test_research_variables():
    assert set(RESEARCH_TEMPLATE.input_variables) == {
        "query",
        "context",
        "research_notes",
    }


def test_citation_variables():
    assert set(CITATION_EXTRACTION_TEMPLATE.input_variables) == {
        "answer",
        "chunks",
    }


def test_summary_variables():
    assert set(CONVERSATION_SUMMARY_TEMPLATE.input_variables) == {
        "conversation",
    }


def test_query_rewrite_template_contains_variables():
    template = QUERY_REWRITE_TEMPLATE

    assert set(template.input_variables) == {
        "conversation_context",
        "query",
    }


def test_retrieval_analysis_variables():
    assert set(RETRIEVAL_ANALYSIS_TEMPLATE.input_variables) == {
        "query",
        "context",
    }


def test_research_template_variables():
    assert set(RESEARCH_TEMPLATE.input_variables) == {
        "query",
        "context",
        "research_notes",
    }


def test_summarizer_variables():
    assert set(SUMMARIZER_TEMPLATE.input_variables) == {
        "history",
        "query",
        "context",
    }


def test_citation_template_variables():
    assert set(CITATION_EXTRACTION_TEMPLATE.input_variables) == {
        "answer",
        "chunks",
    }


def test_summary_template_variables():
    assert set(CONVERSATION_SUMMARY_TEMPLATE.input_variables) == {
        "conversation",
    }


def test_query_rewrite_system_prompt():
    system = QUERY_REWRITE_TEMPLATE.messages[0].prompt.template

    assert "NEVER translate the query" in system
    assert "Preserve the original language" in system
    assert "Output ONLY the rewritten query" in system


def test_summarizer_prompt_contains_rules():
    system = SUMMARIZER_TEMPLATE.messages[0].prompt.template

    assert "Answer in the same language" in system
    assert "Never translate names" in system
    assert "Always ground your answer" in system


def test_citation_prompt_mentions_json():
    system = CITATION_EXTRACTION_TEMPLATE.messages[0].prompt.template

    assert "JSON" in system
    assert "chunk_id" in system
    assert "relevance_score" in system


def test_summary_prompt_word_limit():
    system = CONVERSATION_SUMMARY_TEMPLATE.messages[0].prompt.template

    assert "500 words" in system


def test_query_rewrite_template():
    assert isinstance(QUERY_REWRITE_TEMPLATE, ChatPromptTemplate)


def test_retrieval_analysis_template():
    assert isinstance(RETRIEVAL_ANALYSIS_TEMPLATE, ChatPromptTemplate)


def test_research_template():
    assert isinstance(RESEARCH_TEMPLATE, ChatPromptTemplate)


def test_summarizer_template():
    assert isinstance(SUMMARIZER_TEMPLATE, ChatPromptTemplate)


def test_citation_template():
    assert isinstance(CITATION_EXTRACTION_TEMPLATE, ChatPromptTemplate)


def test_conversation_summary_template():
    assert isinstance(CONVERSATION_SUMMARY_TEMPLATE, ChatPromptTemplate)
