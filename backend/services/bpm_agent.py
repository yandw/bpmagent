import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from backend.services.ai import create_ai_service, IntentType, IntentResult, WebPageAnalysis
from backend.services.browser import create_browser_service, ElementType
from backend.services.ocr import create_ocr_service, OCRResult
from backend.models.user import User, UserSession, TaskHistory
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BPMAgentService:
    """BPM代理核心服务类"""
    
    def __init__(self, user: User, session: UserSession, db: Session):
        self.user = user
        self.session = session
        self.db = db
        
        # 初始化服务
        self.ai_service = create_ai_service()
        self.browser_service = create_browser_service()
        self.ocr_service = create_ocr_service()
        
        # 对话历史
        self.conversation_history = []
        
        # 当前任务状态
        self.current_task = None
        self.current_page_state = None
        self.extracted_data = {}
        
        logger.info(f"BPM代理服务已初始化，用户: {user.username}, 会话: {session.session_id}")
    
    async def process_user_message_stream(self, message: str, message_type: str = "text") -> AsyncGenerator[Dict[str, Any], None]:
        """处理用户消息的流式输出版本"""
        try:
            # 记录用户消息
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now(),
                "type": message_type
            })
            
            # 创建任务历史记录
            task_history = TaskHistory(
                user_id=self.user.id,
                task_type="message_processing",
                task_status="processing",
                input_data={"message": message, "message_type": message_type}
            )
            self.db.add(task_history)
            self.db.commit()
            self.db.refresh(task_history)
            
            # AI意图识别
            intent_result = await self.ai_service.recognize_intent(message)
            
            # 发送意图识别结果
            yield {
                "type": "intent",
                "data": {
                    "intent": intent_result.intent.value,
                    "confidence": intent_result.confidence
                }
            }
            
            # 根据意图处理消息 - 流式版本
            async for chunk in self._handle_intent_stream(intent_result, message, task_history):
                yield chunk
            
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            
            # 更新任务状态为失败
            if 'task_history' in locals():
                task_history.status = "failed"
                task_history.bmp_response = f"处理失败: {str(e)}"
                self.db.commit()
            
            yield {
                "type": "error",
                "data": {
                    "message": "抱歉，处理您的请求时出现了错误，请稍后重试。"
                }
            }

    async def process_user_message(self, message: str, message_type: str = "text") -> Dict[str, Any]:
        """处理用户消息的主要入口"""
        try:
            # 记录用户消息
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now(),
                "type": message_type
            })
            
            # 创建任务历史记录
            task_history = TaskHistory(
                user_id=self.user.id,
                task_type="message_processing",
                task_status="processing",
                input_data={"message": message, "message_type": message_type}
            )
            self.db.add(task_history)
            self.db.commit()
            self.db.refresh(task_history)
            
            # AI意图识别
            intent_result = await self.ai_service.recognize_intent(message)
            
            # 根据意图处理消息
            response = await self._handle_intent(intent_result, message, task_history)
            
            # 记录AI响应
            self.conversation_history.append({
                "role": "assistant",
                "content": response.get("message", ""),
                "timestamp": datetime.now(),
                "intent": intent_result.intent.value,
                "actions": response.get("actions", [])
            })
            
            # 更新任务历史
            task_history.ai_analysis = intent_result.dict()
            task_history.bpm_response = response.get("message", "")
            task_history.status = "completed"
            self.db.commit()
            
            return response
            
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            
            # 更新任务状态为失败
            if 'task_history' in locals():
                task_history.status = "failed"
                task_history.bpm_response = f"处理失败: {str(e)}"
                self.db.commit()
            
            return {
                "message": "抱歉，处理您的请求时出现了错误，请稍后重试。",
                "type": "error",
                "actions": []
            }
    
    async def _handle_intent_stream(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> AsyncGenerator[Dict[str, Any], None]:
        """根据意图处理消息 - 流式版本"""
        
        if intent_result.intent == IntentType.FORM_FILLING:
            # 表单填写不需要流式输出，直接返回结果
            result = await self._handle_form_filling(intent_result, message, task_history)
            yield {
                "type": "message",
                "data": result
            }
        
        elif intent_result.intent == IntentType.OCR_PROCESSING:
            # OCR处理不需要流式输出
            result = await self._handle_ocr_request(intent_result, message, task_history)
            yield {
                "type": "message", 
                "data": result
            }
        
        elif intent_result.intent == IntentType.QUESTION_ANSWERING:
            # 问答需要流式输出
            async for chunk in self._handle_question_answering_stream(intent_result, message, task_history):
                yield chunk
        
        elif intent_result.intent == IntentType.DATA_EXTRACTION:
            # 数据提取不需要流式输出
            result = await self._handle_data_extraction(intent_result, message, task_history)
            yield {
                "type": "message",
                "data": result
            }
        
        else:
            # 一般对话需要流式输出
            async for chunk in self._handle_general_conversation_stream(intent_result, message, task_history):
                yield chunk

    async def _handle_intent(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> Dict[str, Any]:
        """根据意图处理消息"""
        
        if intent_result.intent == IntentType.FORM_FILLING:
            return await self._handle_form_filling(intent_result, message, task_history)
        
        elif intent_result.intent == IntentType.OCR_PROCESSING:
            return await self._handle_ocr_request(intent_result, message, task_history)
        
        elif intent_result.intent == IntentType.QUESTION_ANSWERING:
            return await self._handle_question_answering(intent_result, message, task_history)
        
        elif intent_result.intent == IntentType.DATA_EXTRACTION:
            return await self._handle_data_extraction(intent_result, message, task_history)
        
        else:
            return await self._handle_general_conversation(intent_result, message, task_history)
    
    async def _handle_form_filling(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> Dict[str, Any]:
        """处理表单填写意图"""
        try:
            # 检查是否有目标URL
            if not self.session.target_url:
                return {
                    "message": "请先提供要填写的表单页面URL。例如：请帮我填写 https://example.com/form",
                    "type": "request_url",
                    "actions": [{
                        "type": "request_input",
                        "field": "url",
                        "description": "请输入表单页面的URL"
                    }]
                }
            
            # 启动浏览器并导航到目标页面
            if not self.browser_service.browser:
                await self.browser_service.start_browser()
            
            success = await self.browser_service.navigate_to(self.session.target_url)
            if not success:
                return {
                    "message": f"无法打开页面 {self.session.target_url}，请检查URL是否正确。",
                    "type": "error",
                    "actions": []
                }
            
            # 获取页面状态
            self.current_page_state = await self.browser_service.get_current_state()
            
            # AI分析页面
            analysis = await self.ai_service.analyze_webpage(
                self.current_page_state.screenshot,
                self.current_page_state.html_content
            )
            
            # 检查是否需要用户提供数据
            if analysis.required_fields:
                missing_fields = []
                for field in analysis.required_fields:
                    if field not in self.extracted_data:
                        missing_fields.append(field)
                
                if missing_fields:
                    return {
                        "message": f"我已经分析了页面：{self.current_page_state.title}。\n需要填写以下信息：{', '.join(missing_fields)}。\n请提供这些信息，我将帮您自动填写。",
                        "type": "request_data",
                        "actions": [{
                            "type": "page_analysis",
                            "page_info": {
                                "url": self.current_page_state.url,
                                "title": self.current_page_state.title,
                                "page_type": self.current_page_state.page_type
                            },
                            "required_fields": missing_fields,
                            "analysis": analysis.dict()
                        }]
                    }
            
            # 如果有足够的数据，执行自动填写
            fill_result = await self._auto_fill_form(analysis)
            
            if fill_result["success"]:
                return {
                    "message": f"表单填写完成！已成功填写 {len(fill_result['filled_fields'])} 个字段。",
                    "type": "success",
                    "actions": [{
                        "type": "form_filled",
                        "filled_fields": fill_result["filled_fields"],
                        "page_url": self.current_page_state.url
                    }]
                }
            else:
                return {
                    "message": f"表单填写部分完成。成功填写 {len(fill_result['filled_fields'])} 个字段，{len(fill_result['failed_fields'])} 个字段填写失败。",
                    "type": "partial_success",
                    "actions": [{
                        "type": "form_partially_filled",
                        "filled_fields": fill_result["filled_fields"],
                        "failed_fields": fill_result["failed_fields"]
                    }]
                }
                
        except Exception as e:
            logger.error(f"处理表单填写失败: {e}")
            return {
                "message": "表单填写过程中出现错误，请稍后重试。",
                "type": "error",
                "actions": []
            }
    
    async def _handle_ocr_request(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> Dict[str, Any]:
        """处理OCR识别请求"""
        return {
            "message": "请上传需要识别的发票或文档图片，我将为您提取其中的信息。",
            "type": "request_upload",
            "actions": [{
                "type": "request_upload",
                "accept": "image/*",
                "description": "请上传发票或文档图片进行OCR识别"
            }]
        }
    
    async def _handle_question_answering(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> Dict[str, Any]:
        """处理问答意图"""
        # 生成帮助信息
        help_message = """我是您的BPM智能助手，可以帮助您：

🎯 **核心功能**
1. **自动填写表单** - 提供URL，我将智能分析并填写网页表单
2. **OCR文档识别** - 上传发票或文档图片，自动提取关键信息
3. **智能对话交互** - 通过自然语言与我交流，获得个性化帮助

💡 **使用示例**
- "请帮我填写 https://example.com/form 这个表单"
- "识别这张发票的信息"
- "如何使用自动填表功能？"

📋 **当前会话状态**
- 会话ID: {session_id}
- 目标URL: {target_url}
- 已提取数据: {data_count} 项

请告诉我您需要什么帮助？""".format(
            session_id=self.session.session_id,
            target_url=self.session.target_url or "未设置",
            data_count=len(self.extracted_data)
        )
        
        return {
            "message": help_message,
            "type": "help",
            "actions": [{
                "type": "help_info",
                "capabilities": [
                    "form_filling",
                    "ocr_processing", 
                    "question_answering",
                    "data_extraction"
                ]
            }]
        }
    
    async def _handle_data_extraction(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> Dict[str, Any]:
        """处理数据提取意图"""
        # 尝试从用户消息中提取结构化数据
        extracted_info = await self._extract_structured_data(message)
        
        if extracted_info:
            # 更新已提取的数据
            self.extracted_data.update(extracted_info)
            
            # 如果当前有页面状态，尝试填写表单
            if self.current_page_state:
                fill_result = await self._auto_fill_form_with_data(extracted_info)
                
                if fill_result["success"]:
                    return {
                        "message": f"已提取并填写数据：{', '.join(extracted_info.keys())}。表单填写成功！",
                        "type": "success",
                        "actions": [{
                            "type": "data_extracted_and_filled",
                            "extracted_data": extracted_info,
                            "filled_fields": fill_result["filled_fields"]
                        }]
                    }
                else:
                    return {
                        "message": f"已提取数据：{', '.join(extracted_info.keys())}。但表单填写遇到问题，请检查页面状态。",
                        "type": "partial_success",
                        "actions": [{
                            "type": "data_extracted",
                            "extracted_data": extracted_info
                        }]
                    }
            else:
                return {
                    "message": f"已提取数据：{', '.join(extracted_info.keys())}。请先打开要填写的表单页面。",
                    "type": "data_stored",
                    "actions": [{
                        "type": "data_extracted",
                        "extracted_data": extracted_info
                    }]
                }
        else:
            return {
                "message": "未能从您的消息中提取到结构化数据。请提供更具体的信息，例如：姓名：张三，电话：13800138000",
                "type": "request_clarification",
                "actions": [{
                    "type": "request_structured_data",
                    "examples": [
                        "姓名：张三",
                        "电话：13800138000", 
                        "邮箱：zhangsan@example.com",
                        "地址：北京市朝阳区"
                    ]
                }]
            }
    
    async def _handle_general_conversation_stream(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> AsyncGenerator[Dict[str, Any], None]:
        """处理一般对话 - 流式版本"""
        try:
            # 构建上下文
            context = {
                "user_message": message,
                "session_status": "active",
                "extracted_data_count": len(self.extracted_data)
            }
            
            # 使用AI服务生成流式回复
            full_response = ""
            async for chunk in self.ai_service.generate_response_stream(message, context):
                full_response += chunk
                yield {
                    "type": "message_chunk",
                    "data": {
                        "content": chunk,
                        "message_type": "conversation"
                    }
                }
            
            # 发送完成信号
            yield {
                "type": "message_complete",
                "data": {
                    "full_message": full_response,
                    "message_type": "conversation",
                    "intent": intent_result.intent.value,
                    "actions": [{
                        "type": "general_response",
                        "context": context
                    }]
                }
            }
            
            # 记录完整响应到对话历史
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now(),
                "intent": intent_result.intent.value,
                "actions": [{
                    "type": "general_response",
                    "context": context
                }]
            })
            
            # 更新任务历史
            task_history.ai_analysis = intent_result.dict()
            task_history.bmp_response = full_response
            task_history.status = "completed"
            self.db.commit()
            
        except Exception as e:
            logger.error(f"处理一般对话失败: {e}")
            yield {
                "type": "error",
                "data": {
                    "message": "我正在学习如何更好地理解您的需求。请尝试更具体地描述您需要的帮助。"
                }
            }

    async def _handle_question_answering_stream(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> AsyncGenerator[Dict[str, Any], None]:
        """处理问答 - 流式版本"""
        try:
            # 构建上下文
            context = {
                "user_message": message,
                "session_status": "active",
                "extracted_data": self.extracted_data
            }
            
            # 使用AI服务生成流式回复
            full_response = ""
            async for chunk in self.ai_service.generate_response_stream(message, context):
                full_response += chunk
                yield {
                    "type": "message_chunk",
                    "data": {
                        "content": chunk,
                        "message_type": "question_answer"
                    }
                }
            
            # 发送完成信号
            yield {
                "type": "message_complete",
                "data": {
                    "full_message": full_response,
                    "message_type": "question_answer",
                    "intent": intent_result.intent.value,
                    "actions": [{
                        "type": "question_answer",
                        "context": context
                    }]
                }
            }
            
            # 更新任务历史
            task_history.ai_analysis = intent_result.dict()
            task_history.bmp_response = full_response
            task_history.status = "completed"
            self.db.commit()
            
        except Exception as e:
            logger.error(f"处理问答失败: {e}")
            yield {
                "type": "error",
                "data": {
                    "message": "抱歉，我暂时无法回答您的问题。请稍后重试。"
                }
            }

    async def _handle_general_conversation(self, intent_result: IntentResult, message: str, task_history: TaskHistory) -> Dict[str, Any]:
        """处理一般对话"""
        # 使用AI生成回复
        try:
            # 构建上下文
            context = f"用户消息: {message}\n当前会话状态: 活跃\n已提取数据: {len(self.extracted_data)} 项"
            
            # 生成回复（这里简化处理，实际可以调用AI服务）
            response_message = "我理解您的需求。作为BPM助手，我可以帮助您自动填写表单、识别文档信息。请告诉我您具体需要什么帮助？"
            
            return {
                "message": response_message,
                "type": "conversation",
                "actions": [{
                    "type": "general_response",
                    "context": context
                }]
            }
            
        except Exception as e:
            logger.error(f"处理一般对话失败: {e}")
            return {
                "message": "我正在学习如何更好地理解您的需求。请尝试更具体地描述您需要的帮助。",
                "type": "fallback",
                "actions": []
            }
    
    async def _auto_fill_form(self, analysis: WebPageAnalysis) -> Dict[str, Any]:
        """自动填写表单"""
        filled_fields = []
        failed_fields = []
        
        try:
            # 遍历页面元素，尝试填写
            for element in self.current_page_state.elements:
                if element.element_type in [ElementType.INPUT, ElementType.TEXTAREA, ElementType.SELECT]:
                    # 根据元素名称匹配数据
                    field_value = self._match_field_value(element.name, element.element_type)
                    
                    if field_value:
                        try:
                            if element.element_type == ElementType.INPUT or element.element_type == ElementType.TEXTAREA:
                                success = await self.browser_service.input_text(element.selector, field_value)
                            elif element.element_type == ElementType.SELECT:
                                success = await self.browser_service.select_option(element.selector, field_value)
                            else:
                                success = False
                            
                            if success:
                                filled_fields.append({
                                    "field": element.name,
                                    "value": field_value,
                                    "type": element.element_type.value
                                })
                            else:
                                failed_fields.append({
                                    "field": element.name,
                                    "reason": "填写操作失败"
                                })
                                
                        except Exception as e:
                            failed_fields.append({
                                "field": element.name,
                                "reason": f"填写异常: {str(e)}"
                            })
            
            return {
                "success": len(failed_fields) == 0,
                "filled_fields": filled_fields,
                "failed_fields": failed_fields
            }
            
        except Exception as e:
            logger.error(f"自动填写表单失败: {e}")
            return {
                "success": False,
                "filled_fields": filled_fields,
                "failed_fields": failed_fields + [{"field": "unknown", "reason": str(e)}]
            }
    
    async def _auto_fill_form_with_data(self, data: Dict[str, str]) -> Dict[str, Any]:
        """使用指定数据填写表单"""
        filled_fields = []
        failed_fields = []
        
        try:
            if not self.current_page_state:
                return {"success": False, "filled_fields": [], "failed_fields": [{"field": "page", "reason": "页面未加载"}]}
            
            # 遍历要填写的数据
            for field_name, field_value in data.items():
                # 查找匹配的页面元素
                matching_element = self._find_matching_element(field_name)
                
                if matching_element:
                    try:
                        if matching_element.element_type in [ElementType.INPUT, ElementType.TEXTAREA]:
                            success = await self.browser_service.input_text(matching_element.selector, field_value)
                        elif matching_element.element_type == ElementType.SELECT:
                            success = await self.browser_service.select_option(matching_element.selector, field_value)
                        else:
                            success = False
                        
                        if success:
                            filled_fields.append({
                                "field": field_name,
                                "value": field_value,
                                "element": matching_element.name
                            })
                        else:
                            failed_fields.append({
                                "field": field_name,
                                "reason": "填写操作失败"
                            })
                            
                    except Exception as e:
                        failed_fields.append({
                            "field": field_name,
                            "reason": f"填写异常: {str(e)}"
                        })
                else:
                    failed_fields.append({
                        "field": field_name,
                        "reason": "未找到匹配的页面元素"
                    })
            
            return {
                "success": len(failed_fields) == 0,
                "filled_fields": filled_fields,
                "failed_fields": failed_fields
            }
            
        except Exception as e:
            logger.error(f"使用数据填写表单失败: {e}")
            return {
                "success": False,
                "filled_fields": filled_fields,
                "failed_fields": failed_fields + [{"field": "unknown", "reason": str(e)}]
            }
    
    def _match_field_value(self, field_name: str, element_type: ElementType) -> Optional[str]:
        """根据字段名称匹配已提取的数据"""
        field_name_lower = field_name.lower()
        
        # 定义字段映射规则
        field_mappings = {
            'name': ['name', 'username', 'fullname', '姓名', '用户名'],
            'email': ['email', 'mail', '邮箱', '电子邮件'],
            'phone': ['phone', 'tel', 'mobile', '电话', '手机', '联系电话'],
            'address': ['address', 'addr', '地址', '联系地址'],
            'company': ['company', 'organization', '公司', '单位', '机构'],
            'amount': ['amount', 'money', 'price', '金额', '价格', '费用'],
            'date': ['date', 'time', '日期', '时间']
        }
        
        # 查找匹配的数据
        for data_key, data_value in self.extracted_data.items():
            # 直接匹配
            if data_key.lower() == field_name_lower:
                return str(data_value)
            
            # 模糊匹配
            for mapping_key, keywords in field_mappings.items():
                if data_key.lower() in [k.lower() for k in keywords]:
                    if any(keyword in field_name_lower for keyword in keywords):
                        return str(data_value)
        
        return None
    
    def _find_matching_element(self, field_name: str):
        """查找匹配的页面元素"""
        if not self.current_page_state:
            return None
        
        field_name_lower = field_name.lower()
        
        # 遍历页面元素，查找最匹配的
        best_match = None
        best_score = 0
        
        for element in self.current_page_state.elements:
            if element.element_type in [ElementType.INPUT, ElementType.TEXTAREA, ElementType.SELECT]:
                element_name_lower = element.name.lower()
                
                # 计算匹配分数
                score = 0
                if field_name_lower == element_name_lower:
                    score = 100  # 完全匹配
                elif field_name_lower in element_name_lower or element_name_lower in field_name_lower:
                    score = 80   # 包含匹配
                elif any(word in element_name_lower for word in field_name_lower.split()):
                    score = 60   # 词汇匹配
                
                if score > best_score:
                    best_score = score
                    best_match = element
        
        return best_match if best_score > 50 else None
    
    async def _extract_structured_data(self, message: str) -> Dict[str, str]:
        """从用户消息中提取结构化数据"""
        try:
            # 使用AI服务提取数据
            extracted_data = {}
            
            # 简单的正则表达式提取（实际应该使用更复杂的NLP）
            import re
            
            # 提取姓名
            name_patterns = [
                r'姓名[：:]\s*([^\s,，]+)',
                r'我叫([^\s,，]+)',
                r'名字是([^\s,，]+)'
            ]
            for pattern in name_patterns:
                match = re.search(pattern, message)
                if match:
                    extracted_data['name'] = match.group(1)
                    break
            
            # 提取电话
            phone_patterns = [
                r'电话[：:]\s*(\d{11})',
                r'手机[：:]\s*(\d{11})',
                r'联系电话[：:]\s*(\d{11})',
                r'(\d{11})'
            ]
            for pattern in phone_patterns:
                match = re.search(pattern, message)
                if match:
                    extracted_data['phone'] = match.group(1)
                    break
            
            # 提取邮箱
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            match = re.search(email_pattern, message)
            if match:
                extracted_data['email'] = match.group(1)
            
            # 提取地址
            address_patterns = [
                r'地址[：:]\s*([^\n]+)',
                r'住址[：:]\s*([^\n]+)',
                r'联系地址[：:]\s*([^\n]+)'
            ]
            for pattern in address_patterns:
                match = re.search(pattern, message)
                if match:
                    extracted_data['address'] = match.group(1).strip()
                    break
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"提取结构化数据失败: {e}")
            return {}
    
    async def process_ocr_result(self, ocr_result: OCRResult) -> Dict[str, Any]:
        """处理OCR识别结果"""
        try:
            # 验证OCR结果
            if not ocr_result:
                return {
                    "message": "OCR识别失败，未收到识别结果。请确保图片清晰且包含发票内容。",
                    "type": "error",
                    "actions": [{
                        "type": "request_upload",
                        "accept": "image/*",
                        "description": "请重新上传清晰的发票图片"
                    }]
                }
            
            # 检查OCR是否成功
            if not ocr_result.success:
                error_msg = ocr_result.error or "未知错误"
                return {
                    "message": f"OCR识别失败：{error_msg}。请确保图片清晰且包含发票内容。",
                    "type": "error",
                    "actions": [{
                        "type": "request_upload",
                        "accept": "image/*",
                        "description": "请重新上传清晰的发票图片"
                    }]
                }
            
            # 将OCR结果转换为结构化数据
            ocr_data = {}
            
            # 基础发票信息
            if ocr_result.invoice_number:
                ocr_data['invoice_number'] = ocr_result.invoice_number
            if ocr_result.invoice_date:
                ocr_data['invoice_date'] = ocr_result.invoice_date
            if ocr_result.invoice_type:
                ocr_data['invoice_type'] = ocr_result.invoice_type
                
            # 金额信息
            if ocr_result.total_amount:
                ocr_data['total_amount'] = str(ocr_result.total_amount)
            if ocr_result.tax_amount:
                ocr_data['tax_amount'] = str(ocr_result.tax_amount)
            if ocr_result.net_amount:
                ocr_data['net_amount'] = str(ocr_result.net_amount)
                
            # 公司信息
            if ocr_result.seller_name:
                ocr_data['seller_name'] = ocr_result.seller_name
            if ocr_result.seller_tax_id:
                ocr_data['seller_tax_id'] = ocr_result.seller_tax_id
            if ocr_result.buyer_name:
                ocr_data['buyer_name'] = ocr_result.buyer_name
            if ocr_result.buyer_tax_id:
                ocr_data['buyer_tax_id'] = ocr_result.buyer_tax_id
                
            # 商品明细
            if hasattr(ocr_result, 'items') and ocr_result.items:
                ocr_data['items'] = ocr_result.items
            
            # 检查置信度
            confidence = getattr(ocr_result, 'confidence', 0.0)
            if confidence < 0.8:
                logger.warning(f"OCR识别置信度较低: {confidence}")
                
            # 检查是否提取到有效信息
            if not ocr_data:
                return {
                    "message": "OCR识别完成，但未能提取到有效的发票信息。请确保图片清晰且包含完整的发票内容。",
                    "type": "warning",
                    "actions": [{
                        "type": "request_upload",
                        "accept": "image/*",
                        "description": "请重新上传更清晰的发票图片"
                    }]
                }
            
            # 更新已提取的数据
            self.extracted_data.update(ocr_data)
            
            # 构建成功消息
            extracted_count = len(ocr_data)
            items_count = len(ocr_data.get('items', []))
            confidence_text = f"（识别置信度：{confidence:.1%}）" if confidence > 0 else ""
            
            success_message = f"OCR识别完成！已提取 {extracted_count} 项发票信息"
            if items_count > 0:
                success_message += f"，包含 {items_count} 个商品明细"
            success_message += confidence_text
            
            # 如果当前有页面，尝试自动填写
            if self.current_page_state:
                fill_result = await self._auto_fill_form_with_data(ocr_data)
                
                if fill_result["success"]:
                    return {
                        "message": f"{success_message}，并已自动填写到表单中。",
                        "type": "success",
                        "actions": [{
                            "type": "ocr_processed_and_filled",
                            "ocr_data": ocr_data,
                            "filled_fields": fill_result["filled_fields"],
                            "confidence": confidence
                        }]
                    }
                else:
                    return {
                        "message": f"{success_message}，但自动填写遇到问题。",
                        "type": "partial_success",
                        "actions": [{
                            "type": "ocr_processed",
                            "ocr_data": ocr_data,
                            "fill_errors": fill_result["failed_fields"],
                            "confidence": confidence
                        }]
                    }
            else:
                return {
                    "message": f"{success_message}。请打开要填写的表单页面，我将自动填写这些信息。",
                    "type": "success",
                    "actions": [{
                        "type": "ocr_processed",
                        "ocr_data": ocr_data,
                        "confidence": confidence
                    }]
                }
                
        except Exception as e:
            logger.error(f"处理OCR结果失败: {e}")
            return {
                "message": "处理OCR结果时出现系统错误，请稍后重试。",
                "type": "error",
                "actions": [{
                    "type": "request_upload",
                    "accept": "image/*",
                    "description": "请重新上传发票图片"
                }]
            }
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.browser_service and self.browser_service.browser:
                await self.browser_service.close_browser()
            logger.info(f"BPM代理服务已清理，会话: {self.session.session_id}")
        except Exception as e:
            logger.error(f"清理BPM代理服务失败: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        return {
            "session_id": self.session.session_id,
            "user": self.user.username,
            "target_url": self.session.target_url,
            "conversation_length": len(self.conversation_history),
            "extracted_data_count": len(self.extracted_data),
            "current_page": self.current_page_state.url if self.current_page_state else None,
            "session_status": self.session.status
        }