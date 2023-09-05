import sys
from pathlib import Path
from colorama import Fore

sys.path.append(str(Path(__file__).parent.parent))

from g4f import BaseProvider, models, Provider

logging = False

class Styles:
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def main():
    providers = get_providers()
    failed_providers = []

    for _provider in providers:
        if _provider.needs_auth:
            continue
        print("Provider:", _provider.__name__)
        result = test(_provider)
        print("Result:", result)
        if _provider.working and not result:
            failed_providers.append(_provider)

    print()

    if failed_providers:
        print(f"{Fore.RED + Styles.BOLD}Failed providers:{Styles.ENDC}")
        for _provider in failed_providers:
            print(f"{Fore.RED}{_provider.__name__}")
    else:
        print(f"{Fore.GREEN + Styles.BOLD}All providers are working")


def get_providers() -> list[type[BaseProvider]]:
    provider_names = dir(Provider)
    ignore_names = [
        "annotations",
        "base_provider",
        "BaseProvider",
        "AsyncProvider",
        "AsyncGeneratorProvider"
    ]
    provider_names = [
        provider_name
        for provider_name in provider_names
        if not provider_name.startswith("__") and provider_name not in ignore_names
    ]
    return [getattr(Provider, provider_name) for provider_name in provider_names]


def create_response(_provider: type[BaseProvider]) -> str:
    if _provider.supports_gpt_35_turbo:
        model = models.gpt_35_turbo.name    
    elif _provider.supports_gpt_4:
        model = models.gpt_4.name
    else:
        model = models.default.name
    response = _provider.create_completion(
        model=model,
        messages=[{"role": "user", "content": "Hello, who are you? Answer in detail much as possible."}],
        stream=False,
    )
    return "".join(response)

    
def test(_provider: type[BaseProvider]) -> bool:
    try:
        response = create_response(_provider)
        assert type(response) is str
        assert len(response) > 0
        return response
    except Exception as e:
        if logging:
            print(e)
        return False


if __name__ == "__main__":
    main()
