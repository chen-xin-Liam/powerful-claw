import os
import threading
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class LocalModel:
    name: str
    model_id: str
    size: str
    min_memory: str
    description: str
    is_downloaded: bool = False

class LocalModelService:
    MODELS_DIR = "./models"

    AVAILABLE_MODELS = [
        LocalModel(
            name="Qwen2-0.5B",
            model_id="Qwen/Qwen2-0.5B-Instruct",
            size="~1GB",
            min_memory="2GB",
            description="超轻量中文对话模型，速度极快"
        ),
        LocalModel(
            name="DeepSeek-V4-Pro",
            model_id="deepseek-ai/DeepSeek-V4-Pro",
            size="~8GB",
            min_memory="10GB",
            description="DeepSeek高性能多模态模型"
        ),
        LocalModel(
            name="Qwen2-1.5B",
            model_id="Qwen/Qwen2-1.5B-Instruct",
            size="~3GB",
            min_memory="4GB",
            description="轻量中文对话模型，效果较好"
        ),
        LocalModel(
            name="Phi-3-mini",
            model_id="microsoft/Phi-3-mini-4k-instruct",
            size="~8GB",
            min_memory="8GB",
            description="微软轻量级推理模型，英文能力强"
        ),
        LocalModel(
            name="Qwen2-0.5B-JPN",
            model_id="Qwen/Qwen2-0.5B-JPN-Instruct",
            size="~1GB",
            min_memory="2GB",
            description="日语专项对话模型"
        ),
        LocalModel(
            name="Gemma-2B",
            model_id="google/gemma-2b-it",
            size="~5GB",
            min_memory="4GB",
            description="谷歌轻量对话模型"
        ),
    ]

    def __init__(self):
        self.current_model = None
        self.tokenizer = None
        self.model = None
        self.is_loading = False
        self.is_loaded = False
        self._ensure_models_dir()
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    def _ensure_models_dir(self):
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.MODELS_DIR, "huggingface"), exist_ok=True)

    def list_models(self) -> List[Dict[str, Any]]:
        downloaded_models = self._get_downloaded_models()
        result = []
        for model in self.AVAILABLE_MODELS:
            result.append({
                "name": model.name,
                "model_id": model.model_id,
                "size": model.size,
                "min_memory": model.min_memory,
                "description": model.description,
                "is_downloaded": model.model_id in downloaded_models
            })
        return result

    def _get_downloaded_models(self) -> List[str]:
        downloaded = []
        hf_dir = os.path.join(self.MODELS_DIR, "huggingface")
        if os.path.exists(hf_dir):
            for root, dirs, files in os.walk(hf_dir):
                if "config.json" in files and ("model.safetensors" in files or "pytorch_model.bin" in files or "model.bin" in files):
                    rel_path = os.path.relpath(root, hf_dir)
                    if rel_path != ".":
                        model_id = rel_path.replace("--", "/")
                        downloaded.append(model_id)
        return downloaded

    def is_model_downloaded(self, model_id: str) -> bool:
        model_path = os.path.join(self.MODELS_DIR, "huggingface", "--".join(model_id.split("/")))
        return os.path.exists(model_path)

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        for model in self.AVAILABLE_MODELS:
            if model.name == model_name:
                return {
                    "name": model.name,
                    "model_id": model.model_id,
                    "size": model.size,
                    "min_memory": model.min_memory,
                    "description": model.description,
                    "is_downloaded": self.is_model_downloaded(model.model_id)
                }
        return None

    def load_model(self, model_name: str, progress_callback=None) -> Dict[str, Any]:
        is_custom_model = "/" in model_name

        if is_custom_model:
            model_id = model_name
            display_name = model_name
        else:
            model_info = next((m for m in self.AVAILABLE_MODELS if m.name == model_name), None)
            if not model_info:
                available = ", ".join([m.name for m in self.AVAILABLE_MODELS])
                return {"success": False, "message": f"未知模型: {model_name}\n可用模型: {available}\n也可以直接输入HuggingFace模型ID"}
            model_id = model_info.model_id
            display_name = model_name

        if self.is_loading:
            return {"success": False, "message": "模型正在加载中..."}

        if self.is_loaded and self.current_model == display_name:
            return {"success": True, "message": f"模型 {display_name} 已加载", "model": display_name}

        self.is_loading = True
        self.current_model = display_name

        def load_in_thread():
            try:
                os.environ["TRANSFORMERS_CACHE"] = os.path.abspath(self.MODELS_DIR)
                os.environ["HF_HOME"] = os.path.abspath(self.MODELS_DIR)
                os.environ["HUGGINGFACE_HUB_CACHE"] = os.path.abspath(os.path.join(self.MODELS_DIR, "huggingface"))
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

                if progress_callback:
                    try:
                        progress_callback({"status": "downloading", "message": f"正在下载模型 {display_name}..."})
                    except Exception as e:
                        logger.debug("进度回调失败(downloading)", exc_info=True)

                from transformers import AutoTokenizer, AutoModelForCausalLM

                if progress_callback:
                    try:
                        progress_callback({"status": "loading", "message": f"正在加载模型 {display_name}..."})
                    except Exception as e:
                        logger.debug("进度回调失败(loading)", exc_info=True)

                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    cache_dir=os.path.join(self.MODELS_DIR, "huggingface")
                )

                self.model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    cache_dir=os.path.join(self.MODELS_DIR, "huggingface"),
                    low_cpu_mem_usage=True,
                    torch_dtype="auto",
                    device_map="auto"
                )

                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                self.is_loaded = True
                self.is_loading = False

                if progress_callback:
                    try:
                        progress_callback({"status": "complete", "message": f"模型 {display_name} 加载完成"})
                    except Exception as e:
                        logger.debug("进度回调失败(complete)", exc_info=True)

            except Exception as e:
                self.is_loading = False
                self.is_loaded = False
                self.current_model = None
                self.tokenizer = None
                self.model = None

                error_msg = f"加载模型失败: {str(e)}"
                logger.error(error_msg, exc_info=True)

                if progress_callback:
                    try:
                        progress_callback({"status": "error", "message": error_msg})
                    except Exception as e:
                        logger.debug("进度回调失败(error)", exc_info=True)

        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

        return {"success": True, "message": f"开始加载模型 {display_name}", "model": display_name}

    def unload_model(self):
        if self.is_loading:
            return {"success": False, "message": "模型正在加载中，无法卸载"}

        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.current_model = None

        import gc
        gc.collect()

        return {"success": True, "message": "模型已卸载"}

    def _clean_response(self, response: str) -> str:
        """清理响应中的特殊标记"""
        if not response:
            return ""
        
        # 移除特殊token
        special_tokens = ["<|im_start|>", "<|im_end|>", "<|endoftext|>", "<s>", "</s>", "<pad>"]
        for token in special_tokens:
            response = response.replace(token, "")
        
        # 移除多余的空格和换行
        response = ' '.join(response.split())
        
        return response.strip()

    def chat_stream(self, prompt: str, max_new_tokens: int = 512) -> Generator[str, None, None]:
        if not self.is_loaded or not self.model or not self.tokenizer:
            yield "错误：模型未加载"
            return

        try:
            from threading import Thread
            from queue import Queue

            # 使用支持Markdown格式的提示词，用户输入和AI回答有明显区分
            text = f"""你是一个AI助手，请用中文回答问题。

---

## 📝 用户输入
{prompt}

---

## 🤖 AI回答
"""

            inputs = self.tokenizer([text], return_tensors="pt")
            if hasattr(inputs, 'to'):
                inputs = {k: v.to(self.model.device) if hasattr(v, 'to') else v for k, v in inputs.items()}

            result_queue = Queue()
            self._streaming = True

            def generate_response():
                try:
                    generation_output = self.model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        temperature=0.7,
                        do_sample=True,
                        pad_token_id=self.tokenizer.pad_token_id if self.tokenizer.pad_token_id else self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id
                    )
                    full_response = self.tokenizer.decode(generation_output[0], skip_special_tokens=False)
                    result_queue.put(full_response)
                except Exception as e:
                    result_queue.put(f"错误：{str(e)}")

            thread = Thread(target=generate_response, daemon=True)
            thread.start()

            thread.join(timeout=120)
            self._streaming = False

            if not result_queue.empty():
                full_response = result_queue.get()
                
                # 提取回答部分（从"## 🤖 AI回答"后面开始）
                response_only = ""
                if "## 🤖 AI回答" in full_response:
                    response_only = full_response.split("## 🤖 AI回答")[-1].strip()
                elif "## AI回答" in full_response:
                    response_only = full_response.split("## AI回答")[-1].strip()
                else:
                    response_only = full_response[len(text):].strip()
                
                clean_response = self._clean_response(response_only)

                for char in clean_response:
                    yield char
            else:
                yield "生成超时"

        except Exception as e:
            yield f"错误：{str(e)}"

    def chat(self, prompt: str, max_new_tokens: int = 512) -> str:
        if not self.is_loaded or not self.model or not self.tokenizer:
            return "错误：模型未加载"

        try:
            # 使用支持Markdown格式的提示词，用户输入和AI回答有明显区分
            text = f"""你是一个AI助手，请用中文回答问题。

---

## 📝 用户输入
{prompt}

---

## 🤖 AI回答
"""

            inputs = self.tokenizer([text], return_tensors="pt")

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id if self.tokenizer.pad_token_id else self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )

            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
            
            # 提取回答部分（从"答："后面开始）
            response_only = ""
            if "答：" in full_response:
                response_only = full_response.split("答：")[-1].strip()
            else:
                response_only = full_response[len(text):].strip()
            
            return self._clean_response(response_only)

        except Exception as e:
            return f"错误：{str(e)}"