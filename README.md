# Project Freeroam (prfr)

Open-world sandbox in a Telegram bot.

## Translations

### .lang file syntax

- Labels are placed on separate lines with a following syntax: `label_name=text of the label`

- Empty lines are ignored.

- Lines starting with `#` are ignored and are considered comments.

- `\n` symbols are replaced with newlines in label texts.

- Text in curly brackets `{}` can be replaced with a value by the bot:

    ```text
    info_text=balance: {balance} $
    ```

    The bot will be able to replace `{balance}` with a value:

    ```text
    balance: 2409 $
    ```

- If you want to continue a label on the next line, use `\` at the end of the line and continue the label text on the next line like that:

    ```text
    label_name=label text \
    continued label text
    ```

    is the same as

    ```text
    label_name=label text continued label text
    ```

- Start a label definition with `!` to create a constant that you can use in another labels and change at any time:

    ```text
    !cur=$
    info_text=balance: {balance} [cur]
    ```

    is the same as

    ```text
    info_text=balance: {balance} $
    ```

    Keep in mind that a constant is not a label, and the bot won't be able to use it.

- Since the bot uses HTML parse mode, you can use HTML tags to format the text. See [Telegram formatting options](https://core.telegram.org/bots/api#formatting-options) for more info.
