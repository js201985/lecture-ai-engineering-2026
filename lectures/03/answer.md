# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
"3レベル"で質問すると正しくglossary.jsonの内容を返答していた。間違えて"レベル3"とした時はわからないという返答を正確に返していた。

- `--trace` で見えたツール呼び出し（ツール名と引数）：
--- trace ---
[tool call]   search_glossary({'query': 'LoRA'})
[tool call]   search_glossary({'query': 'QLoRA'})
[tool return] search_glossary -> [{"term": "LoRA", "lecture": 2, "definition": "事前学習済みの重みは固定したまま、重みの更新分を2つの小さな行列の積（低ランク行列）で表し、その小さな行列だけを学習するPEFT手法。学習するパラ…
[tool return] search_glossary -> [{"term": "QLoRA", "lecture": 2, "definition": "ベースモデルの重みを4ビットなどに量子化してメモリを節約したうえで、LoRAで学習する手法。より大きなモデルを小さなGPUで扱える。本講座の第2…
[usage] RunUsage(cost=Decimal('0.0007863'), details={'text_prompt_tokens': 1196}, input_text_tokens=1196, input_tokens=1196, output_tokens=171, requests=2, tool_calls=2)

- 1つの質問での LLM 呼び出し回数（`requests`）：
2回(requests=2)

- 追加したツールと、docstring に書いた説明：
"make_quiz"
"""指定した回の用語から1つを選び、確認問題と答えを返す。
第2回の確認問題を出して」の様に、復習用の問題を求められた時に使う。"""


## 宿題

- 取り組んだレベル：実装 

- やったこと：
make_quiz, get_lecture_summaryが呼び出された際、必ずCLIでログをleaning_logに追記するかどうか確認したうえで、追記していくProgramに変更をした。

- 結果：
利用者の確認を挟んだlogの保存機能を追加できた

- 気づき・疑問：
発展のPiの使い方について解説してほしいです。
Pi Install後の挙動で何が正しいのかよくわからなくなった。
