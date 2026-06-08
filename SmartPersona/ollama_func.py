import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


OLLAMA_AVAILABLE = True


import asyncio


class Ollama_func:
    def __init__(self, model_name="llama3.1:8b"):
        self.model_name = model_name

        if not OLLAMA_AVAILABLE:
            logger.warning(
                "Warning: ollama package is not installed. Install with: pip install ollama"
            )
            self.ollama_client = None
        else:
            try:
                import ollama

                self.ollama_client = ollama
            except Exception as e:
                logger.warning(f"Warning: Ollama client initialization failed: {e}")
                self.ollama_client = None

    def send_prompt(
        self,
        prompt,
        system_prompt=None,
        max_tokens=512,
        temperature=0.7,
        operation_context=None,
    ):
        """Send a prompt to AI and return the response.
        operation_context: optional string to identify the caller (e.g. 'resources_recommendations', 'report_guidance[content]') for clearer timing logs.
        """
        if self.ollama_client is None:
            return "Ollama client not available."
        if prompt is None:
            return "Prompt is required."
        if system_prompt is None:
            system_prompt = "You are a smart and helpful assistant."

        try:
            response = self.ollama_client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": temperature, "num_predict": max_tokens},
            )

            return response["message"]["content"].strip()
        except Exception as e:
            return f"AI API error: {e}"

    def analyze_image(self, image_path, subject_area=None):
        """
        Analyze an image and return the analysis.

        This function expects an image file path, and a subject_area string (optional) for context.
        """
        if self.ollama_client is None:
            return "Ollama client not available."
        if not image_path:
            return "Image path is required."
        if subject_area is None:
            return "Subject area is required."

        # The file path must point to a valid image file.
        try:
            # Read the image as bytes
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
        except Exception as e:
            return f"Failed to read the image file: {e}"

        # Compose a prompt for the AI model to analyze the image
        prompt = (
            "You are an expert academic visual analysis assistant. "
            f"The following image relates to the subject: {subject_area}. "
            "Provide a clear, helpful description and analysis of the image content, "
            "including any relevant context, observations, features, and potential academic insights."
        )

        # Prepare message (the way api_academic/Flask endpoints assemble for cs_pdf)
        try:
            response = self.ollama_client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": "<image>",
                    },  # Place-holder if the API call supports images natively
                ],
                image=image_bytes,
                options={"temperature": 0.7, "num_predict": 700},
            )
            # The Ollama client is assumed to accept image bytes as an argument, or else
            # you will need to adapt this according to your actual Ollama/prediction API
            return (
                response.get("message", {}).get("content", "").strip()
                or "No analysis returned."
            )
        except Exception as e:
            return f"Ollama API error during image analysis: {e}"

    def analyze_data(
        self, file_path, subject_area=None, wizard_extra_prompt_suffix=None
    ):
        # Prepare the extraction content holder
        extracted_content = {}
        if (
            getattr(self, "pdf_helper", None) is None
            or getattr(self, "docx_helper", None) is None
        ):
            return "Document extraction helpers not available. Install cs_pdf with Pdf_helper and Docx_helper."

        # --- IMPLEMENT TIMER ---
        timer = Timer()
        timer.start("analyze_data")
        try:
            # Determine file type and extract content using improved internal methods
            ext = os.path.splitext(file_path)[-1].lower()
            if ext == ".pdf":
                extracted_content = {
                    "text_content": self.pdf_helper.extract_from_pdf(file_path),
                    "sections": [],
                    "metadata": {"file_type": "pdf"},
                }
            elif ext in (".docx", ".doc"):
                extracted_content = {
                    "text_content": self.docx_helper.extract_from_docx(file_path),
                    "sections": [],
                    "metadata": {"file_type": ext.lstrip(".")},
                }
            elif ext in (".csv", ".xlsx", ".xls"):
                # Data files: read with pandas and build text for analysis
                try:
                    import pandas as pd

                    if ext == ".csv":
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)
                    max_rows = 100
                    head = df.head(max_rows)
                    content_str = head.to_string(max_colwidth=80)
                    if len(df) > max_rows:
                        content_str += f"\n... ({len(df) - max_rows} more rows)"
                    extracted_content = {
                        "text_content": content_str,
                        "sections": [],
                        "metadata": {"rows": len(df), "columns": list(df.columns)},
                    }
                except ImportError:
                    timer.end("analyze_data")
                    return "pandas is required to analyze CSV/Excel files. Install with: pip install pandas openpyxl"
                except Exception as e:
                    logger.exception("Failed to read data file")
                    timer.end("analyze_data")
                    return f"Failed to read data file: {str(e)}"
            else:
                timer.end("analyze_data")
                return "Unsupported file type."

            # Backward compatibility: older extractors may still return plain text.
            if isinstance(extracted_content, str):
                extracted_content = {
                    "text_content": extracted_content,
                    "sections": [],
                    "metadata": {"file_type": ext.lstrip(".")},
                }

            # Retrieve the main text after extraction
            content = extracted_content.get("text_content", "")
            if not content.strip():
                timer.end("analyze_data")
                return "No text content extracted from the file."

            try:
                from data_analysis_prompts import (
                    DATA_ANALYSIS_SYSTEM_PROMPT_TABULAR,
                    TABULAR_DATASET_EVALUATION_AND_ML_INSTRUCTIONS,
                )
            except ImportError:
                try:
                    from .data_analysis_prompts import (
                        DATA_ANALYSIS_SYSTEM_PROMPT_TABULAR,
                        TABULAR_DATASET_EVALUATION_AND_ML_INSTRUCTIONS,
                    )
                except ImportError:
                    DATA_ANALYSIS_SYSTEM_PROMPT_TABULAR = "You are an expert data scientist. Evaluate tabular data and suggest appropriate analyses."
                    TABULAR_DATASET_EVALUATION_AND_ML_INSTRUCTIONS = ""

            is_tabular = ext in (".csv", ".xlsx", ".xls")

            if (
                is_tabular
                and str(TABULAR_DATASET_EVALUATION_AND_ML_INSTRUCTIONS).strip()
            ):
                if subject_area:
                    system_prompt = (
                        f"You are an expert data scientist specializing in {subject_area}. "
                        "Evaluate the tabular sample and suggest statistical and ML approaches grounded in the columns shown."
                    )
                else:
                    system_prompt = DATA_ANALYSIS_SYSTEM_PROMPT_TABULAR
                meta = extracted_content.get("metadata", {})
                meta_line = ""
                if meta:
                    meta_line = (
                        "\nMetadata: "
                        + ", ".join(f"{k}: {v}" for k, v in meta.items() if v)
                        + "\n"
                    )
                prompt = (
                    "TABULAR DATA (sample from the uploaded file — use only what appears below):\n"
                    f"{meta_line}\n"
                    f"{content}\n\n"
                    "Analyse this dataset for a university student report. "
                    f"{TABULAR_DATASET_EVALUATION_AND_ML_INSTRUCTIONS}"
                )
            else:
                # Determine system prompt based on subject_area (documents)
                if subject_area:
                    system_prompt = (
                        f"You are an expert document analyst specializing in {subject_area}. "
                        "Your task is to analyze the ACTUAL content provided in the document. "
                        "You must base your analysis ONLY on the specific information found in the document. "
                        "NEVER use placeholders, brackets, or template text like [SPECIFIC SUBJECT] or [specify the phenomena]. "
                        "Always provide concrete, specific details from the actual document content."
                    )
                else:
                    system_prompt = (
                        "You are an expert document analyst. "
                        "Your task is to analyze the ACTUAL content provided in the document. "
                        "You must base your analysis ONLY on the specific information found in the document. "
                        "NEVER use placeholders, brackets, or template text like [SPECIFIC SUBJECT] or [specify the phenomena]. "
                        "Always provide concrete, specific details from the actual document content."
                    )

                headers = extracted_content.get("sections", [])
                meta = extracted_content.get("metadata", {})
                if headers:
                    header_text = (
                        "\nSection headers or major topics detected:\n"
                        + "\n".join([h["text"] for h in headers if "text" in h])
                    )
                else:
                    header_text = ""
                if meta:
                    meta_text = "\nMetadata: " + ", ".join(
                        f"{k}: {v}" for k, v in meta.items() if v
                    )
                else:
                    meta_text = ""

                prompt = (
                    "CRITICAL INSTRUCTIONS: Analyze the ACTUAL document content provided below. "
                    "You MUST base your analysis EXCLUSIVELY on the specific information found in this document. "
                    "DO NOT use placeholders, brackets, or template text. DO NOT write generic templates. "
                    "DO NOT use phrases like [SPECIFIC SUBJECT], [specify the phenomena], [state hypotheses], or any similar placeholders.\n\n"
                    "REQUIREMENTS:\n"
                    "- Extract and analyze ONLY the actual information present in the document\n"
                    "- Use specific details, numbers, names, and facts from the document\n"
                    "- If information is not present in the document, do not invent or use placeholders\n"
                    "- Provide concrete analysis based on what is actually written\n"
                    "- Reference specific sections, data points, and findings from the document\n\n"
                    f"{meta_text}\n"
                    f"{header_text}\n\n"
                    "DOCUMENT CONTENT TO ANALYZE:\n"
                    f"{content}\n\n"
                    "Based on the ACTUAL content above, provide a detailed analysis and summary. "
                    "Use only information that appears in the document. Do not use any placeholders or template text."
                )
            if wizard_extra_prompt_suffix and str(wizard_extra_prompt_suffix).strip():
                prompt += "\n" + str(wizard_extra_prompt_suffix).strip()

            if self.ollama_client is None:
                timer.end("analyze_data")
                return "Ollama client not available."

            response_text = self.send_prompt(
                prompt,
                subject_area=subject_area,
                system_prompt=system_prompt,
                max_tokens=2048,
                temperature=0.2,
            )

            # Optional verification loop: use Gemini as verifier (cross-provider).
            # This reduces ungrounded claims by forcing a supportedness check against SOURCE.
            enable_verification = os.getenv(
                "ENABLE_VERIFICATION", "1"
            ).strip().lower() in ("1", "true", "yes", "on")
            if enable_verification:
                try:
                    threshold = float(os.getenv("HALLUCINATION_RATE_THRESHOLD", "0.10"))
                except Exception:
                    threshold = 0.10
                try:
                    max_retries = int(os.getenv("MAX_VERIFICATION_RETRIES", "1"))
                except Exception:
                    max_retries = 1

                source_text = build_source_from_document(
                    content,
                    max_chars=int(os.getenv("VERIFICATION_SOURCE_MAX_CHARS", "20000")),
                )

                verifier_llm_call = None
                try:
                    from gemini_script import Gemini_functions

                    gemini_verifier = Gemini_functions()

                    def _gemini_llm_call(
                        prompt_text: str,
                        system_prompt_text: str,
                        max_tokens: int,
                        temperature: float,
                    ) -> str:
                        return gemini_verifier.send_prompt(
                            prompt_text,
                            system_prompt=system_prompt_text,
                            max_tokens=max_tokens,
                            temperature=temperature,
                        )

                    verifier_llm_call = _gemini_llm_call
                except Exception as verifier_exc:
                    logger.info(
                        f"Verification skipped: Gemini verifier unavailable ({verifier_exc})"
                    )

                if verifier_llm_call is not None:
                    # Retry only if hallucination rate is above threshold.
                    current_text = response_text
                    verification_attempts = 0
                    final_rate = None
                    final_supported_indexes = set()
                    final_claims = []
                    for _attempt in range(max_retries + 1):
                        claims = extract_claims_basic(
                            current_text, max_claims=15, min_words=4
                        )
                        supported_indexes = verify_supported_claim_indexes(
                            claims=claims,
                            source_text=source_text,
                            llm_call=verifier_llm_call,
                            max_tokens=int(os.getenv("VERIFIER_MAX_TOKENS", "80")),
                            temperature=0.0,
                        )
                        rate = hallucination_rate(claims, supported_indexes)
                        verification_attempts += 1
                        final_rate = rate
                        final_supported_indexes = supported_indexes or set()
                        final_claims = claims or []

                        if rate <= threshold or not claims:
                            break

                        unsupported_claims = [
                            claims[i]
                            for i in range(len(claims))
                            if i not in supported_indexes
                        ]
                        revision_prompt = (
                            revise_remove_unsupported_instruction(
                                source_text, unsupported_claims
                            )
                            + "\n\nDRAFT:\n"
                            + current_text
                        )
                        current_text = self.send_prompt(
                            revision_prompt,
                            subject_area=subject_area,
                            system_prompt=system_prompt,
                            max_tokens=2048,
                            temperature=0.2,
                        )

                    response_text = current_text

                    # Optional: log verification results to evaluation_results.csv
                    if os.getenv(
                        "LOG_VERIFICATION_TO_EVAL_CSV", "1"
                    ).strip().lower() in ("1", "true", "yes", "on"):
                        append_verification_run_to_eval_csv(
                            endpoint="ollama_script.analyze_data",
                            verifier_name="gemini",
                            claims=final_claims,
                            supported_indexes=final_supported_indexes,
                            threshold=threshold,
                            attempts=verification_attempts,
                            hallucination_rate_value=float(
                                final_rate if final_rate is not None else 0.0
                            ),
                        )

            timer.end("analyze_data")
            time_taken = timer.format_time()
            log_msg = f"Time taken for analyze_data: {time_taken}"
            # Write time and task info to a JSON file
            timer.save_time("analyze_data")
            logger.info(log_msg)
            print(log_msg)
            print(response_text)
            return response_text
        except Exception as e:
            timer.end("analyze_data")
            return f"Ollama API error: {e}"

    def generate_document_review(
        self,
        data: str = "",
        result_table=None,
        investigation_details: str = "",
        objective_details: str = "",
        rag_context: Optional[List] = None,
        profile_str: str = "",
        report_context: Optional[Dict[str, Any]] = None,
        document_metadata: Optional[Dict[str, Any]] = None,
        analysis_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a review from pre-extracted document text and context (course, steps, RAG, etc.).
        Used by document-analysis/review when text is already extracted; does not read a file.
        """
        if self.ollama_client is None:
            return "Ollama client not available."
        rag_context = rag_context or []
        report_context = report_context or {}
        document_metadata = document_metadata or {}
        analysis_context = analysis_context or {}

        parts = [
            "You are an expert academic document reviewer. Based on the following context, provide a clear, helpful review.",
            "",
            "--- Document / extracted text ---",
            (data or "").strip() or "(none)",
            "",
        ]
        if investigation_details:
            parts.extend(
                ["--- Investigation / course context ---", investigation_details, ""]
            )
        if objective_details:
            parts.extend(["--- Objectives / steps ---", objective_details, ""])
        if profile_str:
            parts.extend(["--- Learner profile ---", profile_str, ""])
        if rag_context:
            parts.append("--- RAG context (references) ---")
            for i, ctx in enumerate(rag_context[:10], 1):
                if isinstance(ctx, dict):
                    parts.append(str(ctx))
                else:
                    parts.append(str(ctx))
            parts.append("")
        if report_context:
            parts.extend(["--- Report context ---", str(report_context), ""])
        if document_metadata:
            parts.extend(["--- Document metadata ---", str(document_metadata), ""])
        if analysis_context:
            parts.extend(["--- Analysis context ---", str(analysis_context), ""])
        if result_table is not None:
            parts.extend(["--- Result table ---", str(result_table), ""])

        parts.append(
            "Provide a concise review: strengths, gaps, and suggestions based on the above."
        )
        prompt = "\n".join(parts)

        system_prompt = (
            "You are an expert academic document reviewer. "
            "Give constructive, specific feedback based only on the provided context. "
            "Be concise and actionable."
        )
        return self.send_prompt(
            prompt,
            system_prompt=system_prompt,
            max_tokens=2048,
            temperature=0.3,
        )

    
    def embed_text(self, text: str) -> list:
        """
        Generate an embedding vector for the given text using the Ollama API.
        Returns a list of floats (the embedding) or raises on error.

        If Ollama is not available or embedding fails, returns an empty list.
        """
        import httpx

        # Try to get OLLAMA_BASE_URL and MODEL from environment or app config
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

        url = f"{base_url.rstrip('/')}/api/embeddings"
        payload = {
            "model": embed_model,
            "prompt": text,
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            embedding = data.get("embedding") or data.get("data") or None
            if not embedding or not (
                isinstance(embedding, list) or isinstance(embedding, tuple)
            ):
                logger.error(f"Embedding response missing or invalid: {data}")
                return []
            # Ensure all values are floats
            return [float(x) for x in embedding]
        except Exception as e:
            logger.error(f"Ollama embed_text error: {str(e)}", exc_info=True)
            return []
