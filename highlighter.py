from pygments.lexers.python import PythonLexer
from pygments.token import Token

# VS Code "Dark+" inspired palette
TOKEN_COLORS = {
    Token.Keyword: "#c586c0",
    Token.Keyword.Constant: "#569cd6",
    Token.Name.Builtin: "#4ec9b0",
    Token.Name.Function: "#dcdcaa",
    Token.Name.Class: "#4ec9b0",
    Token.Name.Decorator: "#dcdcaa",
    Token.String: "#ce9178",
    Token.Number: "#b5cea8",
    Token.Comment: "#6a9955",
    Token.Operator: "#d4d4d4",
    Token.Punctuation: "#d4d4d4",
}
DEFAULT_COLOR = "#d4d4d4"

def _color_for(token_type):
    """Walk up the token hierarchy until we find a color match."""
    t = token_type
    while t is not None:
        if t in TOKEN_COLORS:
            return TOKEN_COLORS[t]
        t = t.parent
    return DEFAULT_COLOR

def highlight_python(ctk_textbox, code):
    """
    Applies Python syntax highlighting to a CTkTextbox in place.
    Must be called AFTER the text has already been inserted.
    """
    text_widget = ctk_textbox._textbox  # underlying tkinter.Text widget
    lexer = PythonLexer()

    # Clear any previous syntax tags before re-highlighting
    for tag in text_widget.tag_names():
        if tag.startswith("syn_"):
            text_widget.tag_remove(tag, "1.0", "end")

    configured = set()
    line, col = 1, 0

    for token_type, value in lexer.get_tokens(code):
        length = len(value)
        if length == 0:
            continue

        start_index = f"{line}.{col}"
        newline_count = value.count("\n")
        if newline_count:
            line += newline_count
            col = length - value.rfind("\n") - 1
        else:
            col += length
        end_index = f"{line}.{col}"

        color = _color_for(token_type)
        tag_name = f"syn_{color.strip('#')}"
        if tag_name not in configured:
            text_widget.tag_configure(tag_name, foreground=color)
            configured.add(tag_name)

        text_widget.tag_add(tag_name, start_index, end_index)