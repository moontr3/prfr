import math
import api

locale = api.Locale('lang/en.lang')
word = 'выфыук'

class Brackets:
    def __init__(self,
        at:int
    ):
        self.at: int = at
        self.text: str = ''

out = f'выфыук\n🐵\n'

for key,value in locale.const.items():
    out += f'!{key}={value}\n'

for key,value in locale.strings.items():
    lines = []

    for l in value.split('\n'):
        brackets = []
        is_bracket = False
        words = math.ceil(len(l)/(len(word)+1))

        for index, i in enumerate(l):
            if i == '}':
                is_bracket = False

            if is_bracket:
                brackets[-1].text += i

            if i == '{':
                is_bracket = True
                brackets.append(Brackets(index))

        brackets = brackets[::-1]
        text = [word for _ in range(words)]

        for i in brackets:
            text.insert(min(math.ceil(i.at/(len(word)+1)), words), '{'+i.text+'}')

        text = ' '.join(text)

        lines.append(text)

    lines = "\\n".join(lines)
    out += f'{key}={lines}\n'

with open('lang/vifiuk.lang', 'w', encoding='utf-8') as f:
    f.write(out)