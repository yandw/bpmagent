import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, validator
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationType(str, Enum):
    """验证类型枚举"""
    REQUIRED = "required"
    FORMAT = "format"
    RANGE = "range"
    BUSINESS = "business"
    CROSS_FIELD = "cross_field"


class ValidationSeverity(str, Enum):
    """验证严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult(BaseModel):
    """验证结果模型"""
    field: str
    validation_type: ValidationType
    severity: ValidationSeverity
    message: str
    is_valid: bool
    suggested_value: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ValidationRule(BaseModel):
    """验证规则模型"""
    field: str
    validation_type: ValidationType
    severity: ValidationSeverity
    rule_config: Dict[str, Any]
    error_message: str
    
    class Config:
        use_enum_values = True


class SmartValidationService:
    """智能验证服务"""
    
    def __init__(self):
        self.validation_rules = {}
        self.business_rules = {}
        self._init_default_rules()
        logger.info("智能验证服务已初始化")
    
    def _init_default_rules(self):
        """初始化默认验证规则"""
        
        # 基础格式验证规则
        self.validation_rules.update({
            'email': ValidationRule(
                field='email',
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                rule_config={'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'},
                error_message='邮箱格式不正确'
            ),
            'phone': ValidationRule(
                field='phone',
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                rule_config={'pattern': r'^1[3-9]\d{9}$'},
                error_message='手机号格式不正确，应为11位数字'
            ),
            'id_card': ValidationRule(
                field='id_card',
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                rule_config={'pattern': r'^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$'},
                error_message='身份证号格式不正确'
            ),
            'amount': ValidationRule(
                field='amount',
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                rule_config={'pattern': r'^\d+(\.\d{1,2})?$'},
                error_message='金额格式不正确，应为数字且最多保留两位小数'
            ),
            'date': ValidationRule(
                field='date',
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                rule_config={'pattern': r'^\d{4}-\d{2}-\d{2}$'},
                error_message='日期格式不正确，应为YYYY-MM-DD格式'
            )
        })
        
        # 业务规则
        self.business_rules.update({
            'invoice_amount_consistency': {
                'description': '发票金额一致性检查',
                'fields': ['total_amount', 'tax_amount', 'net_amount'],
                'rule': lambda data: self._validate_invoice_amount_consistency(data)
            },
            'date_range_check': {
                'description': '日期范围合理性检查',
                'fields': ['invoice_date', 'due_date'],
                'rule': lambda data: self._validate_date_range(data)
            },
            'company_info_consistency': {
                'description': '公司信息一致性检查',
                'fields': ['seller_name', 'seller_tax_id', 'buyer_name', 'buyer_tax_id'],
                'rule': lambda data: self._validate_company_info(data)
            }
        })
    
    def validate_field(self, field_name: str, field_value: Any, context: Dict[str, Any] = None) -> List[ValidationResult]:
        """验证单个字段"""
        results = []
        
        try:
            # 必填验证
            if self._is_required_field(field_name) and not field_value:
                results.append(ValidationResult(
                    field=field_name,
                    validation_type=ValidationType.REQUIRED,
                    severity=ValidationSeverity.ERROR,
                    message=f'{field_name} 是必填字段',
                    is_valid=False
                ))
                return results
            
            # 如果字段为空且非必填，跳过其他验证
            if not field_value:
                return results
            
            # 格式验证
            format_result = self._validate_format(field_name, field_value)
            if format_result:
                results.append(format_result)
            
            # 范围验证
            range_result = self._validate_range(field_name, field_value)
            if range_result:
                results.append(range_result)
            
            # 智能建议
            suggestion_result = self._generate_smart_suggestion(field_name, field_value, context)
            if suggestion_result:
                results.append(suggestion_result)
                
        except Exception as e:
            logger.error(f"验证字段 {field_name} 失败: {e}")
            results.append(ValidationResult(
                field=field_name,
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f'验证过程中出现错误: {str(e)}',
                is_valid=False
            ))
        
        return results
    
    def validate_form_data(self, form_data: Dict[str, Any]) -> List[ValidationResult]:
        """验证整个表单数据"""
        all_results = []
        
        try:
            # 逐字段验证
            for field_name, field_value in form_data.items():
                field_results = self.validate_field(field_name, field_value, form_data)
                all_results.extend(field_results)
            
            # 跨字段验证
            cross_field_results = self._validate_cross_fields(form_data)
            all_results.extend(cross_field_results)
            
            # 业务规则验证
            business_results = self._validate_business_rules(form_data)
            all_results.extend(business_results)
            
        except Exception as e:
            logger.error(f"验证表单数据失败: {e}")
            all_results.append(ValidationResult(
                field='form',
                validation_type=ValidationType.BUSINESS,
                severity=ValidationSeverity.ERROR,
                message=f'表单验证过程中出现错误: {str(e)}',
                is_valid=False
            ))
        
        return all_results
    
    def _validate_format(self, field_name: str, field_value: Any) -> Optional[ValidationResult]:
        """格式验证"""
        # 获取字段类型的验证规则
        field_type = self._infer_field_type(field_name)
        rule = self.validation_rules.get(field_type)
        
        if not rule:
            return None
        
        pattern = rule.rule_config.get('pattern')
        if not pattern:
            return None
        
        value_str = str(field_value).strip()
        
        if not re.match(pattern, value_str):
            # 尝试生成修正建议
            suggested_value = self._suggest_format_correction(field_type, value_str)
            
            return ValidationResult(
                field=field_name,
                validation_type=ValidationType.FORMAT,
                severity=rule.severity,
                message=rule.error_message,
                is_valid=False,
                suggested_value=suggested_value
            )
        
        return ValidationResult(
            field=field_name,
            validation_type=ValidationType.FORMAT,
            severity=ValidationSeverity.INFO,
            message=f'{field_name} 格式正确',
            is_valid=True
        )
    
    def _validate_range(self, field_name: str, field_value: Any) -> Optional[ValidationResult]:
        """范围验证"""
        field_type = self._infer_field_type(field_name)
        
        if field_type == 'amount':
            try:
                amount = Decimal(str(field_value))
                if amount < 0:
                    return ValidationResult(
                        field=field_name,
                        validation_type=ValidationType.RANGE,
                        severity=ValidationSeverity.ERROR,
                        message='金额不能为负数',
                        is_valid=False,
                        suggested_value='0.00'
                    )
                elif amount > Decimal('999999999.99'):
                    return ValidationResult(
                        field=field_name,
                        validation_type=ValidationType.RANGE,
                        severity=ValidationSeverity.WARNING,
                        message='金额过大，请确认是否正确',
                        is_valid=True
                    )
            except (InvalidOperation, ValueError):
                return ValidationResult(
                    field=field_name,
                    validation_type=ValidationType.RANGE,
                    severity=ValidationSeverity.ERROR,
                    message='金额格式无效',
                    is_valid=False
                )
        
        elif field_type == 'date':
            try:
                date_obj = datetime.strptime(str(field_value), '%Y-%m-%d').date()
                today = date.today()
                
                if date_obj > today:
                    return ValidationResult(
                        field=field_name,
                        validation_type=ValidationType.RANGE,
                        severity=ValidationSeverity.WARNING,
                        message='日期为未来日期，请确认是否正确',
                        is_valid=True
                    )
                elif (today - date_obj).days > 365 * 10:  # 超过10年
                    return ValidationResult(
                        field=field_name,
                        validation_type=ValidationType.RANGE,
                        severity=ValidationSeverity.WARNING,
                        message='日期过于久远，请确认是否正确',
                        is_valid=True
                    )
            except ValueError:
                return ValidationResult(
                    field=field_name,
                    validation_type=ValidationType.RANGE,
                    severity=ValidationSeverity.ERROR,
                    message='日期格式无效',
                    is_valid=False
                )
        
        return None
    
    def _validate_cross_fields(self, form_data: Dict[str, Any]) -> List[ValidationResult]:
        """跨字段验证"""
        results = []
        
        # 检查邮箱和手机号至少填写一个
        if 'email' in form_data or 'phone' in form_data:
            email = form_data.get('email', '').strip()
            phone = form_data.get('phone', '').strip()
            
            if not email and not phone:
                results.append(ValidationResult(
                    field='contact',
                    validation_type=ValidationType.CROSS_FIELD,
                    severity=ValidationSeverity.ERROR,
                    message='邮箱和手机号至少需要填写一个',
                    is_valid=False
                ))
        
        # 检查开始日期和结束日期的逻辑关系
        start_date = form_data.get('start_date')
        end_date = form_data.get('end_date')
        
        if start_date and end_date:
            try:
                start = datetime.strptime(str(start_date), '%Y-%m-%d').date()
                end = datetime.strptime(str(end_date), '%Y-%m-%d').date()
                
                if start > end:
                    results.append(ValidationResult(
                        field='date_range',
                        validation_type=ValidationType.CROSS_FIELD,
                        severity=ValidationSeverity.ERROR,
                        message='开始日期不能晚于结束日期',
                        is_valid=False
                    ))
            except ValueError:
                pass  # 日期格式错误会在单字段验证中处理
        
        return results
    
    def _validate_business_rules(self, form_data: Dict[str, Any]) -> List[ValidationResult]:
        """业务规则验证"""
        results = []
        
        for rule_name, rule_config in self.business_rules.items():
            try:
                # 检查是否有相关字段
                has_relevant_fields = any(field in form_data for field in rule_config['fields'])
                
                if has_relevant_fields:
                    rule_result = rule_config['rule'](form_data)
                    if rule_result:
                        results.extend(rule_result)
                        
            except Exception as e:
                logger.error(f"执行业务规则 {rule_name} 失败: {e}")
                results.append(ValidationResult(
                    field='business_rule',
                    validation_type=ValidationType.BUSINESS,
                    severity=ValidationSeverity.WARNING,
                    message=f'业务规则验证异常: {rule_config["description"]}',
                    is_valid=True
                ))
        
        return results
    
    def _validate_invoice_amount_consistency(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证发票金额一致性"""
        results = []
        
        try:
            total_amount = data.get('total_amount')
            tax_amount = data.get('tax_amount')
            net_amount = data.get('net_amount')
            
            if total_amount and tax_amount:
                total = Decimal(str(total_amount))
                tax = Decimal(str(tax_amount))
                
                # 计算不含税金额
                calculated_net = total - tax
                
                if net_amount:
                    net = Decimal(str(net_amount))
                    # 允许小数点后两位的误差
                    if abs(calculated_net - net) > Decimal('0.01'):
                        results.append(ValidationResult(
                            field='amount_consistency',
                            validation_type=ValidationType.BUSINESS,
                            severity=ValidationSeverity.ERROR,
                            message=f'金额不一致：总金额({total}) - 税额({tax}) ≠ 不含税金额({net})',
                            is_valid=False,
                            suggested_value=str(calculated_net)
                        ))
                else:
                    # 如果没有不含税金额，建议填写
                    results.append(ValidationResult(
                        field='net_amount',
                        validation_type=ValidationType.BUSINESS,
                        severity=ValidationSeverity.INFO,
                        message='建议填写不含税金额',
                        is_valid=True,
                        suggested_value=str(calculated_net)
                    ))
                
                # 检查税率合理性
                if total > 0:
                    tax_rate = (tax / total) * 100
                    if tax_rate > 20:  # 税率超过20%
                        results.append(ValidationResult(
                            field='tax_rate',
                            validation_type=ValidationType.BUSINESS,
                            severity=ValidationSeverity.WARNING,
                            message=f'税率({tax_rate:.2f}%)较高，请确认是否正确',
                            is_valid=True
                        ))
                        
        except (InvalidOperation, ValueError, ZeroDivisionError) as e:
            logger.error(f"验证发票金额一致性失败: {e}")
        
        return results
    
    def _validate_date_range(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证日期范围合理性"""
        results = []
        
        try:
            invoice_date = data.get('invoice_date')
            due_date = data.get('due_date')
            
            if invoice_date and due_date:
                invoice_dt = datetime.strptime(str(invoice_date), '%Y-%m-%d').date()
                due_dt = datetime.strptime(str(due_date), '%Y-%m-%d').date()
                
                if due_dt < invoice_dt:
                    results.append(ValidationResult(
                        field='date_logic',
                        validation_type=ValidationType.BUSINESS,
                        severity=ValidationSeverity.ERROR,
                        message='到期日期不能早于开票日期',
                        is_valid=False
                    ))
                
                # 检查付款期限是否合理（通常不超过1年）
                days_diff = (due_dt - invoice_dt).days
                if days_diff > 365:
                    results.append(ValidationResult(
                        field='payment_term',
                        validation_type=ValidationType.BUSINESS,
                        severity=ValidationSeverity.WARNING,
                        message=f'付款期限({days_diff}天)较长，请确认是否正确',
                        is_valid=True
                    ))
                        
        except ValueError as e:
            logger.error(f"验证日期范围失败: {e}")
        
        return results
    
    def _validate_company_info(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证公司信息一致性"""
        results = []
        
        # 检查销售方和购买方不能相同
        seller_name = data.get('seller_name', '').strip()
        buyer_name = data.get('buyer_name', '').strip()
        
        if seller_name and buyer_name and seller_name == buyer_name:
            results.append(ValidationResult(
                field='company_consistency',
                validation_type=ValidationType.BUSINESS,
                severity=ValidationSeverity.ERROR,
                message='销售方和购买方不能相同',
                is_valid=False
            ))
        
        # 检查税号格式（简化版）
        seller_tax_id = data.get('seller_tax_id', '').strip()
        buyer_tax_id = data.get('buyer_tax_id', '').strip()
        
        tax_id_pattern = r'^[0-9A-Z]{15,20}$'
        
        if seller_tax_id and not re.match(tax_id_pattern, seller_tax_id):
            results.append(ValidationResult(
                field='seller_tax_id',
                validation_type=ValidationType.BUSINESS,
                severity=ValidationSeverity.WARNING,
                message='销售方税号格式可能不正确',
                is_valid=True
            ))
        
        if buyer_tax_id and not re.match(tax_id_pattern, buyer_tax_id):
            results.append(ValidationResult(
                field='buyer_tax_id',
                validation_type=ValidationType.BUSINESS,
                severity=ValidationSeverity.WARNING,
                message='购买方税号格式可能不正确',
                is_valid=True
            ))
        
        return results
    
    def _generate_smart_suggestion(self, field_name: str, field_value: Any, context: Dict[str, Any] = None) -> Optional[ValidationResult]:
        """生成智能建议"""
        field_type = self._infer_field_type(field_name)
        value_str = str(field_value).strip()
        
        # 手机号智能建议
        if field_type == 'phone' and len(value_str) == 11 and value_str.isdigit():
            if not value_str.startswith('1'):
                return ValidationResult(
                    field=field_name,
                    validation_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.WARNING,
                    message='手机号通常以1开头，请确认是否正确',
                    is_valid=True,
                    suggested_value=f'1{value_str[1:]}'
                )
        
        # 邮箱智能建议
        elif field_type == 'email' and '@' in value_str:
            common_domains = ['gmail.com', 'qq.com', '163.com', '126.com', 'sina.com', 'hotmail.com']
            domain = value_str.split('@')[-1].lower()
            
            # 检查常见域名的拼写错误
            for common_domain in common_domains:
                if self._calculate_similarity(domain, common_domain) > 0.8 and domain != common_domain:
                    suggested_email = value_str.replace(domain, common_domain)
                    return ValidationResult(
                        field=field_name,
                        validation_type=ValidationType.FORMAT,
                        severity=ValidationSeverity.INFO,
                        message=f'您是否想输入 {suggested_email}？',
                        is_valid=True,
                        suggested_value=suggested_email
                    )
        
        # 金额智能建议
        elif field_type == 'amount':
            try:
                amount = Decimal(value_str)
                # 检查是否缺少小数点
                if '.' not in value_str and amount > 1000:
                    suggested_amount = str(amount / 100)
                    return ValidationResult(
                        field=field_name,
                        validation_type=ValidationType.FORMAT,
                        severity=ValidationSeverity.INFO,
                        message=f'金额较大，您是否想输入 {suggested_amount}？',
                        is_valid=True,
                        suggested_value=suggested_amount
                    )
            except (InvalidOperation, ValueError):
                pass
        
        return None
    
    def _infer_field_type(self, field_name: str) -> str:
        """推断字段类型"""
        field_name_lower = field_name.lower()
        
        if any(keyword in field_name_lower for keyword in ['email', 'mail', '邮箱']):
            return 'email'
        elif any(keyword in field_name_lower for keyword in ['phone', 'tel', 'mobile', '电话', '手机']):
            return 'phone'
        elif any(keyword in field_name_lower for keyword in ['id', 'card', '身份证']):
            return 'id_card'
        elif any(keyword in field_name_lower for keyword in ['amount', 'money', 'price', '金额', '价格']):
            return 'amount'
        elif any(keyword in field_name_lower for keyword in ['date', 'time', '日期', '时间']):
            return 'date'
        else:
            return 'text'
    
    def _is_required_field(self, field_name: str) -> bool:
        """判断字段是否必填"""
        required_keywords = ['name', 'email', 'phone', 'amount', 'date', '姓名', '邮箱', '电话', '金额', '日期']
        field_name_lower = field_name.lower()
        
        return any(keyword in field_name_lower for keyword in required_keywords)
    
    def _suggest_format_correction(self, field_type: str, value: str) -> Optional[str]:
        """建议格式修正"""
        if field_type == 'phone':
            # 移除所有非数字字符
            digits_only = re.sub(r'\D', '', value)
            if len(digits_only) == 11 and digits_only.startswith('1'):
                return digits_only
        
        elif field_type == 'email':
            # 简单的邮箱修正
            if '@' not in value and '.' in value:
                # 可能缺少@符号
                parts = value.split('.')
                if len(parts) >= 2:
                    return f"{parts[0]}@{'.'.join(parts[1:])}"
        
        elif field_type == 'amount':
            # 移除非数字和小数点字符
            cleaned = re.sub(r'[^\d.]', '', value)
            if cleaned and cleaned.replace('.', '').isdigit():
                return cleaned
        
        return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度（简化版Levenshtein距离）"""
        if len(str1) == 0:
            return 0.0 if len(str2) == 0 else 0.0
        if len(str2) == 0:
            return 0.0
        
        # 简化的相似度计算
        common_chars = set(str1) & set(str2)
        total_chars = set(str1) | set(str2)
        
        return len(common_chars) / len(total_chars) if total_chars else 0.0
    
    def add_custom_rule(self, rule: ValidationRule):
        """添加自定义验证规则"""
        self.validation_rules[rule.field] = rule
        logger.info(f"已添加自定义验证规则: {rule.field}")
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """获取验证结果摘要"""
        error_count = sum(1 for r in results if r.severity == ValidationSeverity.ERROR and not r.is_valid)
        warning_count = sum(1 for r in results if r.severity == ValidationSeverity.WARNING)
        info_count = sum(1 for r in results if r.severity == ValidationSeverity.INFO)
        
        return {
            "total_validations": len(results),
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "is_valid": error_count == 0,
            "has_warnings": warning_count > 0,
            "has_suggestions": any(r.suggested_value for r in results)
        }