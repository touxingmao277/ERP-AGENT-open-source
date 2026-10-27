"""Run the local ERP test double on the production MCP default port."""
import uvicorn


def main() -> None:
    uvicorn.run("evals.test_erp.app:create_app", factory=True, host="127.0.0.1", port=8081)


if __name__ == "__main__":
    main()
