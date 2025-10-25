import json
import base64
from typing import Dict, List, Any, Optional, AsyncGenerator
import aiohttp
from .base import BaseAIService, IntentResult, IntentType, WebPageAnalysis, AIMessage


class QwenAIService(BaseAIService):
    """基于阿里百炼Qwen模型的AI服务"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url')
        self.model = config.get('model', 'qwen-max')
    
    async def _call_qwen_api(self, messages: List[Dict[str, Any]], temperature: float = 0.7, stream: bool = False) -> str:
        """调用Qwen API"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': 2000,
            'stream': stream
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.base_url}/chat/completions', 
                                  headers=headers, json=data) as response:
                if stream:
                    # 流式响应处理在 _call_qwen_api_stream 中
                    raise NotImplementedError("Use _call_qwen_api_stream for streaming")
                
                result = await response.json()
                
                if 'error' in result:
                    raise Exception(f"Qwen API错误: {result['error']}")
                
                return result['choices'][0]['message']['content']
    
    async def _call_qwen_api_stream(self, messages: List[Dict[str, Any]], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """调用Qwen API流式接口"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': 2000,
            'stream': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.base_url}/chat/completions', 
                                  headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Qwen API错误: {error_text}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀
                        
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data_json = json.loads(data_str)
                            if 'choices' in data_json and len(data_json['choices']) > 0:
                                delta = data_json['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    async def recognize_intent(self, user_input: str, context: Dict[str, Any] = None) -> IntentResult:
        """识别用户意图"""
        context = context or {}
        
        # 构建系统提示
        system_prompt = """你是一个企业BPM系统的智能助手，专门识别用户的业务流程意图。

支持的意图类型：
1. expense_report - 报销申请（关键词：报销、发票、差旅、餐费、交通费等）
2. leave_request - 请假申请（关键词：请假、休假、年假、病假等）
3. purchase_request - 采购申请（关键词：采购、购买、申请物品等）
4. contract_approval - 合同审批（关键词：合同、协议、审批等）
5. unknown - 未知意图

请分析用户输入，返回JSON格式结果：
{
    "intent": "意图类型",
    "confidence": 0.95,
    "entities": {
        "expense_type": "差旅费",
        "amount": 1500.0,
        "reason": "上海出差"
    }
}"""
        
        # 添加OCR上下文信息
        context_info = ""
        if context.get('ocr_results'):
            context_info = f"\n\n用户还上传了发票，OCR识别结果：{json.dumps(context['ocr_results'], ensure_ascii=False)}"
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"用户输入：{user_input}{context_info}"}
        ]
        
        try:
            response = await self._call_qwen_api(messages, temperature=0.3)
            
            # 解析JSON响应
            result_data = json.loads(response)
            
            return IntentResult(
                intent=IntentType(result_data.get('intent', 'unknown')),
                confidence=result_data.get('confidence', 0.0),
                entities=result_data.get('entities', {}),
                context=context
            )
            
        except Exception as e:
            # 如果AI识别失败，使用关键词匹配作为后备
            return self._fallback_intent_recognition(user_input, context)
    
    def _fallback_intent_recognition(self, user_input: str, context: Dict[str, Any]) -> IntentResult:
        """后备意图识别（基于关键词）"""
        user_input_lower = user_input.lower()
        
        # 报销相关关键词
        expense_keywords = ['报销', '发票', '差旅', '餐费', '交通费', '住宿费', '票据']
        if any(keyword in user_input_lower for keyword in expense_keywords):
            return IntentResult(
                intent=IntentType.EXPENSE_REPORT,
                confidence=0.8,
                entities={},
                context=context
            )
        
        # 请假相关关键词
        leave_keywords = ['请假', '休假', '年假', '病假', '事假']
        if any(keyword in user_input_lower for keyword in leave_keywords):
            return IntentResult(
                intent=IntentType.LEAVE_REQUEST,
                confidence=0.8,
                entities={},
                context=context
            )
        
        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.1,
            entities={},
            context=context
        )
    
    async def analyze_webpage(self, screenshot: bytes, html_content: str = None) -> WebPageAnalysis:
        """分析网页内容"""
        # 将截图转换为base64
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        system_prompt = """你是一个网页分析专家，能够理解网页的结构和功能。
请分析提供的网页截图，识别：
1. 页面类型（login/form/success/error）
2. 表单字段
3. 按钮
4. 错误信息
5. 成功指示器

返回JSON格式结果：
{
    "page_type": "form",
    "form_fields": [
        {"name": "amount", "type": "input", "required": true, "label": "金额"}
    ],
    "buttons": [
        {"text": "提交", "type": "submit", "selector": "button[type=submit]"}
    ],
    "confidence": 0.95
}"""

        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user', 
                'content': [
                    {
                        "type": "text",
                        "text": f"请分析这个网页截图。{f'HTML内容：{html_content[:500]}...' if html_content else ''}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_b64}"
                        }
                    }
                ]
            }
        ]
        
        try:
            response = await self._call_qwen_api(messages, temperature=0.3)
            result_data = json.loads(response)
            
            return WebPageAnalysis(
                page_type=result_data.get('page_type', 'unknown'),
                form_fields=result_data.get('form_fields', []),
                required_fields=[f['name'] for f in result_data.get('form_fields', []) if f.get('required')],
                buttons=result_data.get('buttons', []),
                error_messages=result_data.get('error_messages', []),
                success_indicators=result_data.get('success_indicators', []),
                confidence=result_data.get('confidence', 0.0)
            )
            
        except Exception as e:
            # 返回默认分析结果
            return WebPageAnalysis(
                page_type='unknown',
                confidence=0.0
            )

    async def generate_response_stream(self, user_input: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """生成流式对话回复"""
        context = context or {}
        
        system_prompt = """你是一个智能的BPM助手，专门帮助用户处理企业业务流程。
你的主要功能包括：
1. 协助用户进行报销申请
2. 帮助填写各种表单
3. 识别和处理发票信息
4. 提供业务流程指导

请用友好、专业的语气回复用户，并尽可能提供有用的建议。"""

        # 构建对话历史
        messages = [{'role': 'system', 'content': system_prompt}]
        
        # 添加最近的对话历史
        recent_messages = self.get_recent_messages(5)
        for msg in recent_messages:
            messages.append({
                'role': msg.role,
                'content': msg.content
            })
        
        # 添加当前用户输入
        messages.append({'role': 'user', 'content': user_input})
        
        try:
            full_response = ""
            async for chunk in self._call_qwen_api_stream(messages, temperature=0.7):
                full_response += chunk
                yield chunk
            
            # 添加到对话历史
            self.add_message('user', user_input)
            self.add_message('assistant', full_response)
            
        except Exception as e:
            error_msg = f"抱歉，我暂时无法处理您的请求。错误信息：{str(e)}"
            yield error_msg

    async def generate_response(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """生成对话回复"""
        context = context or {}
        
        system_prompt = """你是一个智能的BPM助手，专门帮助用户处理企业业务流程。
你的主要功能包括：
1. 协助用户进行报销申请
2. 帮助填写各种表单
3. 识别和处理发票信息
4. 提供业务流程指导

请用友好、专业的语气回复用户，并尽可能提供有用的建议。"""

        # 构建对话历史
        messages = [{'role': 'system', 'content': system_prompt}]
        
        # 添加最近的对话历史
        recent_messages = self.get_recent_messages(5)
        for msg in recent_messages:
            messages.append({
                'role': msg.role,
                'content': msg.content
            })
        
        # 添加当前用户输入
        messages.append({'role': 'user', 'content': user_input})
        
        try:
            response = await self._call_qwen_api(messages, temperature=0.7)
            
            # 添加到对话历史
            self.add_message('user', user_input)
            self.add_message('assistant', response)
            
            return response
            
        except Exception as e:
            return f"抱歉，我暂时无法处理您的请求。错误信息：{str(e)}"

    async def generate_question(self, missing_fields: List[str], context: Dict[str, Any]) -> str:
        """生成追问问题"""
        system_prompt = """你是一个友好的企业助手，需要向用户询问缺失的信息。

请根据缺失的字段生成自然、友好的问题。要求：
1. 语气亲切、专业
2. 问题清晰明确
3. 如果有多个字段，可以一次询问多个
4. 提供示例或选项（如果适用）

示例：
- 缺失"成本中心" -> "请问这笔费用应该归属到哪个成本中心呢？（例如：销售部、研发部、市场部）"
- 缺失"项目编号" -> "请提供相关的项目编号，以便正确归档这笔费用。"
"""
        
        context_info = ""
        if context.get('task_type') == 'expense_report':
            context_info = "当前正在处理报销申请，"
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f'{context_info}缺失字段：{", ".join(missing_fields)}'}
        ]
        
        try:
            response = await self._call_qwen_api(messages, temperature=0.7)
            return response.strip()
        except Exception:
            # 后备问题生成
            if len(missing_fields) == 1:
                return f"请提供{missing_fields[0]}信息。"
            else:
                return f"请提供以下信息：{', '.join(missing_fields)}。"
    
    async def extract_answer(self, user_response: str, question_context: Dict[str, Any]) -> Dict[str, Any]:
        """从用户回复中提取答案"""
        missing_fields = question_context.get('missing_fields', [])
        
        system_prompt = f"""你是一个信息提取专家，需要从用户回复中提取对应字段的值。

目标字段：{', '.join(missing_fields)}

请从用户回复中提取对应的值，返回JSON格式：
{{
    "字段名1": "提取的值1",
    "字段名2": "提取的值2"
}}

如果某个字段无法确定，值设为null。
"""
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f'用户回复：{user_response}'}
        ]
        
        try:
            response = await self._call_qwen_api(messages, temperature=0.3)
            return json.loads(response)
        except Exception:
            # 简单的关键词匹配作为后备
            result = {}
            for field in missing_fields:
                if field in user_response:
                    # 尝试提取字段后的内容
                    parts = user_response.split(field)
                    if len(parts) > 1:
                        value = parts[1].strip().split()[0] if parts[1].strip() else None
                        result[field] = value
            return result