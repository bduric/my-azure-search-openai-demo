from typing import Any, Coroutine, Literal, Optional, Union, overload

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
)

from approaches.approach import ThoughtStep
from approaches.chatapproach import ChatApproach
from core.authentication import AuthenticationHelper
from core.modelhelper import get_token_limit


class ChatReadRetrieveReadApproach(ChatApproach):

    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
    """

    def __init__(
        self,
        *,
        search_client: SearchClient,
        auth_helper: AuthenticationHelper,
        openai_client: AsyncOpenAI,
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
    ):
        self.search_client = search_client
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)

    @property
    def system_message_chat_conversation(self):
        return """Assistant helps Virginia Beach residents with their building code questions, and questions about the building permits and zones. Be brief in your answers.
        Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know and ask follow up questions. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
        If question is not clear but there is a table with some information, return tabular information. Present all tabular information as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
        Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, for example [info1.txt]. Don't combine sources, list each source separately, for example [info1.txt][info2.pdf]. Look at the all documents and think step by step.
        here are examples within ++++.
        ++++
        Question: What kind of sign can I put up for my business to advertise a special event like a grand opening or special sale?
        Answer: The City Zoning Ordinance allows each business location only one 32 square foot banner or one 30-foot-tall balloon for three one-week periods per calendar year. A sign permit is required each time a temporary sign is used. 
        Any temporary signs other than those specified above are illegal. Prohibited signs are listed in Section 212 of the City's Zoning Ordinance.
        Steps taken:
        - list characteristics defining a sign to determine what is a sign and what is not
        - search all documents to see rules and check if permits required
        - check if there are any special cases or exceptions and follow the referenced sections and exhibits for approved zone, sign placements and sizes 
        - follow all referenced sections in Article 2 General Requirements under B. Sign Regulations of Zoning Ordinance to to summarize answer and provide reasoning steps
        Question: Can I operate my business from my residence?
        Answer: Home based businesses are allowed under the following circumstances without a conditional use permit:
        -The business use of the home is clearly incidental and subordinate to the residential use of the home.
        -There is no change in the outside appearance of the home or lot and no noise that can be heard from the street or neighboring property.
        -There is no traffic generated beyond what would normally be expected in the neighborhood.
        -Vehicles associated with the business, including customers, are parked in the driveway and not on the street.
        -Only one commercial vehicle is permitted as long as its carrying capacity is 1 ton or less, its height is 7 feet or less, and its length is 20 feet or less.
        -The person operating the business lives in the home.
        -No person other than members of the immediate family, who also live in the home, is employed by the business. (With a conditional use permit, one employee who does not reside in the home is permitted in addition to family members who live in the home.)
        -The business must be located only in the principal structure on the lot; it cannot be in an accessory structure unless a conditional use permit is approved.
        -There are no sales of products or merchandise to the public.
        -No more than one patron, customer, or pupil may be present at one time (unless a conditional use permit is approved).
        The following businesses are specifically not permitted in the home:
        -Convalescent or nursing homes
        -Tourist homes
        -Massage or tattoo parlors
        -Body piercing establishments
        -Radio or television repair shops
        -Auto repair shops
        Some home businesses require a conditional use permit (CUP). Contact the Zoning Office at (757) 385-8074 to find out if a CUP is required. If one is required, it can be obtained through the Planning Department at (757) 385-4621.
        Steps taken:
        - list circumstances home based business is allowed without conditional use permit
        - list business that are specifically not permitted in the home
        - refer to conditional use permit process 
        ++++
        {follow_up_questions_prompt}
        {injected_prompt}
        """

    @overload
    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[False],
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, ChatCompletion]]:
        ...

    @overload
    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[True],
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, AsyncStream[ChatCompletionChunk]]]:
        ...

    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]]]:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top", 3)
        filter = self.build_filter(overrides, auth_claims)
        use_semantic_ranker = True if overrides.get("semantic_ranker") and has_text else False

        original_user_query = history[-1]["content"]
        user_query_request = "Generate search query for: " + original_user_query

        functions = [
            {
                "name": "search_sources",
                "description": "Retrieve sources from the Azure AI Search index",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Query string to retrieve documents from azure search eg: 'Virginia Beach building codes'",
                        }
                    },
                    "required": ["search_query"],
                },
            }
        ]

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        messages = self.get_messages_from_history(
            system_prompt=self.query_prompt_template,
            model_id=self.chatgpt_model,
            history=history,
            user_content=user_query_request,
            max_tokens=self.chatgpt_token_limit - len(user_query_request),
            few_shots=self.query_prompt_few_shots,
        )

        chat_completion: ChatCompletion = await self.openai_client.chat.completions.create(
            messages=messages,  # type: ignore
            # Azure Open AI takes the deployment name as the model name
            model=self.chatgpt_deployment if self.chatgpt_deployment else self.chatgpt_model,
            temperature=0.0,
            max_tokens=100,  # Setting too low risks malformed JSON, setting too high may affect performance
            n=1,
            functions=functions,
            function_call="auto",
        )

        query_text = self.get_search_query(chat_completion, original_user_query)

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors: list[VectorQuery] = []
        if has_vector:
            vectors.append(await self.compute_text_embedding(query_text))

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        if not has_text:
            query_text = None

        results = await self.search(top, query_text, filter, vectors, use_semantic_ranker, use_semantic_captions)

        sources_content = self.get_sources_content(results, use_semantic_captions, use_image_citation=False)
        content = "\n".join(sources_content)

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history

        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        system_message = self.get_system_prompt(
            overrides.get("prompt_template"),
            self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else "",
        )

        response_token_limit = 1024
        messages_token_limit = self.chatgpt_token_limit - response_token_limit
        messages = self.get_messages_from_history(
            system_prompt=system_message,
            model_id=self.chatgpt_model,
            history=history,
            # Model does not handle lengthy system messages well. Moving sources to latest user conversation to solve follow up questions prompt.
            user_content=original_user_query + "\n\nSources:\n" + content,
            max_tokens=messages_token_limit,
        )

        data_points = {"text": sources_content}

        extra_info = {
            "data_points": data_points,
            "thoughts": [
                ThoughtStep(
                    "Original user query",
                    original_user_query,
                ),
                ThoughtStep(
                    "Generated search query",
                    query_text,
                    {"use_semantic_captions": use_semantic_captions, "has_vector": has_vector},
                ),
                ThoughtStep("Results", [result.serialize_for_results() for result in results]),
                ThoughtStep("Prompt", [str(message) for message in messages]),
            ],
        }

        chat_coroutine = self.openai_client.chat.completions.create(
            # Azure Open AI takes the deployment name as the model name
            model=self.chatgpt_deployment if self.chatgpt_deployment else self.chatgpt_model,
            messages=messages,
            temperature=overrides.get("temperature") or 0.7,
            max_tokens=response_token_limit,
            n=1,
            stream=should_stream,
        )
        return (extra_info, chat_coroutine)
