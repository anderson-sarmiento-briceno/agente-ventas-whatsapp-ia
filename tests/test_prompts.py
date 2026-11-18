from agente_vendedor.prompts import cargar_conocimiento, cargar_prompt, renderizar


def test_plantillas_tienen_sus_marcadores():
    assert "{{texto}}" in cargar_prompt("clasificador")
    respuesta = cargar_prompt("respuesta")
    for marcador in ("{{tienda}}", "{{documento}}", "{{pregunta}}"):
        assert marcador in respuesta


def test_conocimiento_sin_lineas_vacias():
    texto = cargar_conocimiento()
    assert "Kennedy, Calle 6 #94A-26" in texto
    assert "\n\n" not in texto


def test_conocimiento_conserva_datos_oficiales():
    texto = cargar_conocimiento()
    for dato in ("8:00 - 19:00", "8:00 - 15:00", "https://wa.me/573178668004", "1 año", "$8.000", "18,8 cm - 19,4 cm"):
        assert dato in texto


def test_skill_de_negocio_al_dia():
    """La skill de Claude Code se genera desde knowledge/: si falla, ejecuta scripts/generar_skill.py."""
    import scripts.generar_skill as g

    assert g.DESTINO.read_text(encoding="utf-8") == g.generar()


def test_renderizar_no_toca_otras_llaves():
    assert renderizar("{json} {{a}} {{b}}", a="1") == "{json} 1 {{b}}"
