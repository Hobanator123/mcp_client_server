import asyncio
from typing import Optional, Tuple
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.types import CallToolResult
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
    
    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith(".py")

        if not is_python:
            raise ValueError("Server script must be a .py file")
        
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        # List available resource endpoints
        response = await self.session.list_resources()
        resources = response.resources
        print("\nConnected to server with resources:", [resource.name for resource in resources])

    async def process_content(self, response_content: list, available_tools: list, messages: list=None, final_text: list=None) -> Tuple[list, list]:
        if not messages:
            messages = []
        if not final_text:
            final_text = []
        # if not assistant_message_content:
        #     assistant_message_content = []
        assistant_message_content = []

        for content in response_content:
            # print(f"######\n{content.type}\n######")
            # print("\t", content)
            if content.type == "text":
                # print("content is text, appending to final_text amd assistant_message_content")
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input
                # print(f"content is tool_use\ntool name: {tool_name}\ntool args: {tool_args}")

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                assistant_message_content.append(content)
                # assistant_message_content.append(result)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Get next response from Claude
                # print("Getting next response from claude passing these messages:")
                # print(messages)
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )

                # print(response.content)
                messages, final_text = await self.process_content(response.content, available_tools, messages, final_text)

        return messages, final_text

    async def process_query(self, query: str) -> str:
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        final_text = []
        messages, final_text = await self.process_content(response.content, available_tools, messages, final_text)

        return "\n".join(final_text)
    
    async def chat_loop(self):
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)
            
            except Exception as e:
                print(f"\nError: {str(e)}")
                type, value, traceback = sys.exc_info()
                print(f"\nError Type: {type}")
                print(f"\nError Traceback: \n{traceback}")


    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
