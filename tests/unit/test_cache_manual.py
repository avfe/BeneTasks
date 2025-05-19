import main

def test_clear_cache_manual():
    # вручную кладём что-то в кэш и очищаем
    main.cache_data["tasks"] = ["dummy"]
    main.clear_cache()
    assert main.cache_data["tasks"] is None
