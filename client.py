import asyncio
import json
import sys

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # ---------------------------------------------------------
    # 1. Tell MCP client how to start the server
    # ---------------------------------------------------------
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.app.main"],
    )

    client = Client(
        stdio_client(params)
    )

    # ---------------------------------------------------------
    # 2. Open MCP connection
    # ---------------------------------------------------------
    async with client:

        # =====================================================
        # LOGIN
        # =====================================================

        print("=== LOGIN ===")

        email = input("Email: ")
        password = input("Password: ")

        login_result = await client.call_tool(
            "login",
            {
                "email": email,
                "password": password,
            },
        )

        login_text = login_result.content[0].text

        print("\nLogin result:")
        print(login_text)

        # Convert JSON text to Python dictionary
        login_data = json.loads(login_text)

        # Stop if login failed
        if "error" in login_data:
            print("\nLogin failed.")
            return

        # Save JWT token in memory
        token = login_data["token"]

        # Save authenticated customer ID
        customer_id = login_data["customer_id"]

        print("\nLogin successful!")
        print(f"Customer ID: {customer_id}")
        print(f"JWT token: {token}")



        # Test admin tool
        admin_result = await client.call_tool(
            "list_all_customers",
            {
                "token": token,
            },
        )

        print("\n=== ALL CUSTOMERS ===")

        if admin_result.content:
            print(admin_result.content[0].text)
        # =====================================================
        # GET CUSTOMER
        # =====================================================

        print("\n=== GET CUSTOMER ===")

        customer_result = await client.call_tool(
            "get_customer",
            {
                "token": token,
                "customer_id": customer_id,
            },
        )

        print(customer_result.content[0].text)

        # =====================================================
        # LIST TICKETS
        # =====================================================

        print("\n=== LIST TICKETS ===")

        tickets_result = await client.call_tool(
            "list_tickets",
            {
                "token": token,
                "customer_id": customer_id,
            },
        )

        print(tickets_result.content[0].text)

        # =====================================================
        # CREATE TICKET
        # =====================================================

        create_ticket = input(
            "\nDo you want to create a ticket? (yes/no): "
        )

        if create_ticket.lower() == "yes":
            issue = input("Describe the issue: ")

            ticket_result = await client.call_tool(
                "create_ticket",
                {
                    "token": token,
                    "customer_id": customer_id,
                    "issue": issue,
                },
            )

            print("\nCreate ticket result:")
            print(ticket_result.content[0].text)

        # =====================================================
        # MCP RESOURCE
        # =====================================================

        print("\n=== SUPPORT POLICY ===")

        resource_result = await client.read_resource(
            "file://support-policy"
        )

        print(resource_result.contents[0].text)

        # =====================================================
        # MCP PROMPT
        # =====================================================

        print("\n=== SUPPORT PROMPT ===")

        prompt_result = await client.get_prompt(
            "support_prompt",
            arguments={
                "issue": "general customer support"
            },
        )

        print(
            prompt_result
            .messages[0]
            .content
            .text
        )


if __name__ == "__main__":
    asyncio.run(main())
