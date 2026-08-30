import asyncio
import json
import sys

from google import genai
from google.genai import errors, types
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client


PROTECTED_TOOLS = {
    "get_customer",
    "create_ticket",
    "list_tickets",
    "list_all_customers",
}

CUSTOMER_SCOPED_TOOLS = {
    "get_customer",
    "create_ticket",
    "list_tickets",
}

ADMIN_TOOLS = {
    "list_all_customers",
}


async def main():
    # =========================================================
    # MCP CONNECTION
    # =========================================================

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.app.main"],
    )

    mcp_client = Client(stdio_client(params))

    async with mcp_client:

        # =====================================================
        # LOGIN
        # =====================================================

        print("=== Login ===")

        email = input("Email: ")
        password = input("Password: ")

        login_result = await mcp_client.call_tool(
            "login",
            {
                "email": email,
                "password": password,
            },
        )

        if not login_result.content:
            print("Login failed: empty response")
            return

        login_data = json.loads(
            login_result.content[0].text
        )

        if "error" in login_data:
            print(f"Login failed: {login_data['error']}")
            return

        token = login_data["token"]
        customer_id = login_data["customer_id"]
        role = login_data["role"]

        print(f"\nLogin successful.")
        print(f"Customer ID: {customer_id}")
        print(f"Role: {role}")

        # =====================================================
        # MCP RESOURCE
        # =====================================================

        resource_result = await mcp_client.read_resource(
            "file://support-policy"
        )

        support_policy = resource_result.contents[0].text

        # =====================================================
        # MCP PROMPT
        # =====================================================

        prompt_result = await mcp_client.get_prompt(
            "support_prompt",
            arguments={
                "issue": "general customer support"
            },
        )

        support_prompt = (
            prompt_result.messages[0].content.text
        )

        # =====================================================
        # SYSTEM CONTEXT
        # =====================================================

        system_context = f"""
            {support_prompt}

            SUPPORT POLICY:
            {support_policy}

            AUTHENTICATION:
            Customer ID: {customer_id}
            Role: {role}

            RULES:
            - The user is already authenticated.
            - Never ask for JWT tokens or passwords.
            - Customers can access only their own data.
            - Admins can access all customers.
            - Only admins can use admin operations.
            - If a non-admin asks for admin data, explain that permission is denied.
            - If the user wants to create a ticket without providing an issue, ask for it.
            - Do not call get_customer unless customer information is needed.
            - Use create_ticket when the issue is known.
            - Use list_tickets when the user asks about tickets.
        """

        # =====================================================
        # DISCOVER MCP TOOLS
        # =====================================================

        tools_response = await mcp_client.list_tools()

        print("\nMCP tools:")
        for tool in tools_response.tools:
            print(f"- {tool.name}")

        # =====================================================
        # CONVERT MCP TOOLS → GEMINI TOOLS
        # =====================================================

        function_declarations = []

        for tool in tools_response.tools:

            # Application handles login
            if tool.name == "login":
                continue

            # Hide admin tools from normal customers
            if tool.name in ADMIN_TOOLS and role != "admin":
                continue

            schema = dict(tool.input_schema)

            properties = dict(
                schema.get("properties", {})
            )

            required = list(
                schema.get("required", [])
            )

            # Hide JWT from Gemini
            if tool.name in PROTECTED_TOOLS:
                properties.pop("token", None)

                if "token" in required:
                    required.remove("token")

            # Hide customer ID because app knows it
            if tool.name in CUSTOMER_SCOPED_TOOLS:
                properties.pop("customer_id", None)

                if "customer_id" in required:
                    required.remove("customer_id")

            schema["properties"] = properties
            schema["required"] = required

            function_declarations.append({
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            })

        gemini_tools = types.Tool(
            function_declarations=function_declarations
        )

        # =====================================================
        # GEMINI
        # =====================================================

        llm = genai.Client()

        chat = llm.aio.chats.create(
            model="gemini-3.6-flash",
            config=types.GenerateContentConfig(
                tools=[gemini_tools],
                system_instruction=system_context,
            ),
        )

        print("\nCustomer Support Agent")
        print("Type 'exit' to stop.")

        # =====================================================
        # CONVERSATION
        # =====================================================

        while True:
            user_query = input("\nYou: ")

            if user_query.lower() in {"exit", "quit"}:
                print("Assistant: Goodbye!")
                break

            try:
                response = await chat.send_message(
                    user_query
                )

            except errors.ClientError as error:
                if error.code == 429:
                    print("\nGemini quota exceeded. Try again later.")
                    continue

                raise

            # =================================================
            # TOOL LOOP
            # =================================================

            while True:
                function_call = None

                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_call = part.function_call
                        break

                # Gemini returned normal text
                if function_call is None:
                    print(f"\nAssistant:\n{response.text}")
                    break

                print(
                    f"\nGemini chose: {function_call.name}"
                )

                tool_args = dict(function_call.args)

                # Inject JWT
                if function_call.name in PROTECTED_TOOLS:
                    tool_args["token"] = token

                # Inject logged-in customer's ID
                if function_call.name in CUSTOMER_SCOPED_TOOLS:
                    tool_args["customer_id"] = customer_id

                print(f"MCP arguments: {tool_args}")

                # =============================================
                # EXECUTE MCP TOOL
                # =============================================

                tool_result = await mcp_client.call_tool(
                    function_call.name,
                    tool_args,
                )

                if tool_result.content:
                    tool_text = tool_result.content[0].text
                else:
                    tool_text = "{}"

                print(f"MCP result:\n{tool_text}")

                # =============================================
                # STRUCTURED TOOL RESULT
                # =============================================

                try:
                    tool_data = json.loads(tool_text)
                except json.JSONDecodeError:
                    tool_data = {"message": tool_text}

                if isinstance(tool_data, dict) and "error" in tool_data:
                    gemini_result = {
                        "success": False,
                        "error": tool_data["error"],
                    }
                else:
                    gemini_result = {
                        "success": True,
                        "data": tool_data,
                    }

                function_response = (
                    types.Part.from_function_response(
                        name=function_call.name,
                        response=gemini_result,
                    )
                )

                try:
                    response = await chat.send_message(
                        function_response
                    )

                except errors.ClientError as error:
                    if error.code == 429:
                        print(
                            "\nGemini quota exceeded. "
                            "Try again later."
                        )
                        break

                    raise


if __name__ == "__main__":
    asyncio.run(main())
