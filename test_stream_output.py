#!/usr/bin/env python3
"""
测试流式输出功能的脚本
"""
import asyncio
import websockets
import json
import uuid
from datetime import datetime

async def test_stream_output():
    """测试流式输出功能"""
    # 使用真实的会话ID
    session_id = "3a6af99f-16bc-4bfd-90e6-81b1e7d30639"
    
    # 测试token（使用真实的JWT token）
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc2MTQ5MDQ4MX0.fOa0qk5p2MVecO6faKTxMRIHa-C9F4hVN1Lb6pwTlV0"
    
    # WebSocket连接URL
    ws_url = f"ws://localhost:8888/api/chat/ws/{session_id}?token={token}"
    
    print(f"🚀 开始测试流式输出功能")
    print(f"📝 会话ID: {session_id}")
    print(f"🔗 连接URL: {ws_url}")
    print("-" * 50)
    
    try:
        # 建立WebSocket连接
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket连接成功")
            
            # 接收欢迎消息
            welcome_msg = await websocket.recv()
            print(f"📨 欢迎消息: {welcome_msg}")
            
            # 发送测试消息
            test_message = {
                "message": "请帮我介绍一下什么是BPM（业务流程管理），以及它的主要特点和应用场景。",
                "type": "text",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📤 发送测试消息: {test_message['message']}")
            await websocket.send(json.dumps(test_message))
            
            # 接收流式响应
            print("\n🔄 开始接收流式响应:")
            print("-" * 30)
            
            message_chunks = []
            complete_message = None
            
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "message_chunk":
                        # 流式消息块
                        chunk_content = data.get("content", "")
                        message_chunks.append(chunk_content)
                        print(f"📦 接收到消息块: '{chunk_content}'")
                        
                    elif data.get("type") == "message_complete":
                        # 消息完成
                        complete_message = data
                        print(f"✅ 消息完成: {data.get('content', '')}")
                        print(f"🎯 意图识别: {data.get('intent', 'N/A')}")
                        break
                        
                    elif data.get("type") == "status":
                        # 状态消息
                        print(f"📊 状态更新: {data.get('message', '')}")
                        
                    elif data.get("type") == "error":
                        # 错误消息
                        print(f"❌ 错误: {data.get('message', '')}")
                        break
                        
                    else:
                        print(f"📋 其他消息: {data}")
                        
                except asyncio.TimeoutError:
                    print("⏰ 接收超时，结束测试")
                    break
                except Exception as e:
                    print(f"❌ 接收消息时出错: {e}")
                    break
            
            print("-" * 30)
            print("📊 测试结果统计:")
            print(f"   - 接收到的消息块数量: {len(message_chunks)}")
            print(f"   - 消息块内容: {message_chunks}")
            if complete_message:
                print(f"   - 完整消息长度: {len(complete_message.get('content', ''))}")
                print(f"   - 意图识别结果: {complete_message.get('intent', 'N/A')}")
            
            # 验证流式输出的完整性
            if message_chunks and complete_message:
                chunks_combined = "".join(message_chunks)
                complete_content = complete_message.get("content", "")
                
                if chunks_combined == complete_content:
                    print("✅ 流式输出完整性验证通过")
                else:
                    print("❌ 流式输出完整性验证失败")
                    print(f"   块组合长度: {len(chunks_combined)}")
                    print(f"   完整消息长度: {len(complete_content)}")
            
    except websockets.exceptions.ConnectionClosed:
        print("❌ WebSocket连接已关闭")
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
    
    print("\n🏁 流式输出功能测试完成")

if __name__ == "__main__":
    asyncio.run(test_stream_output())