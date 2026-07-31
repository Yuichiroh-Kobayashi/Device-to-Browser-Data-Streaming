# Device-to-Browser Data Streaming

[English](README.md) | 日本語

このリポジトリでは、デバイスが取得した測定値やサンプリングデータを
Webブラウザへ継続的に送信するための、ベンダー非依存アプリケーション
プロファイルおよび参照設計である`d2b-stream`を規定します。

`d2b-stream`はHTTP/1.1やWebSocketを置き換えるものではなく、これらの
標準技術を利用します。本仕様が定義する範囲は、それらの上位層における
アプリケーションフレーミング、セッション状態、サンプル識別、時刻、
およびデータ欠落の意味論です。

この日本語READMEはリポジトリ案内のための翻訳です。規範的な要件については、
英語のプロトコル仕様書および各profile仕様書を参照してください。

## 現行仕様

現在のプロトコルバージョンは`0.1`です。次の事項を定義しています。

* HTTPによるデバイス検出と読み取り専用ステータス取得
* WebSocket text frameによるstrict JSON control message
* 正確に32 bytesのlittle-endian共通envelopeとprofile別binary payload
* monotonic timestamp、sample-frame sequence、明示的なgap
* `vi-measurement`および`pcm-audio` profile
* 完全一致によるstream parameter negotiation
* 任意で利用できるpairing-token認証
* 1つのactive stream session owner
* 機微情報を除いた公開statusと、認証済みcontrol connection上の詳細status

最初に[プロトコル仕様書](docs/protocol-v0.1.md)を参照してください。

独立した実装に必要な補足事項は、次の文書で説明しています。

* [アーキテクチャ](docs/architecture.md)
* [ブラウザ参照parser](docs/browser-reference-parser.md)
* [実装ガイダンス](docs/implementation-guidance.md)
* [deployment guide](docs/deployment-guide.md)
* [conformance matrix](docs/conformance-matrix.md)
* 各profile仕様書

[先行事例およびプロトコル選定レポート](docs/prior-art-and-protocol-selection.md)では、
serial通信、Bluetooth Low Energy、broker型通信、実験室向けstreaming stackを
そのまま採用するのではなく、既存のWeb標準を組み合わせた理由を説明しています。

V/I測定値の
[SenML mapping](docs/profiles/vi-measurement-senml-mapping.md)は、
compactなlive binary profileを置き換えるものではなく、exportおよび
相互運用のための層を定義します。

## リポジトリ構成

* `docs/`

  * 規範的application profile
  * profile仕様
  * security
  * browser compatibility
  * 先行事例
  * 相互運用
  * validation関連文書
* `schemas/`

  * 自己完結したJSON Schema Draft 2020-12形式のcontrol message schema
  * capabilities schema
* `test-vectors/`

  * JSON形式のcontrol、capabilities、binary frame golden vectors
* `tools/validate_test_vectors.py`

  * schema構造、strict control fixture、binary frame、continuity、
    mutation testを検証するPython標準ライブラリのみのvalidator
* `tools/generate_test_vectors.py`

  * JSON形式のgolden vectorsを決定的に生成するPython標準ライブラリのみのgenerator

すべてのvectorを検証するには、次を実行します。

```sh
python3 tools/validate_test_vectors.py
```

このutilityは、次の項目を検査します。

* JSON syntax
* Draft 2020-12宣言
* local referenceの存在
* fixtureで使用するJSON Schema相当の制約
* golden result
* 対象を限定したmutation test

このutility自体は、JSON Schema meta-schemaによる完全な検証を行いません。

golden vectorsを意図的に再生成する場合は、次を実行します。

```sh
python3 tools/generate_test_vectors.py
```

このリポジトリには、次のものを含めません。

* 製品固有firmware
* WebSocket server実装
* browser application
* binary recording
* runtime dependency

## 状態とライセンス

Version `0.1`はpre-1.0段階のプロトコルです。互換性規則は
[versioning policy](docs/versioning-policy.md)で定義しています。

特記のない限り、このリポジトリの仕様書、schema、test vectorおよびtoolは
Apache License 2.0で提供します。
Copyright 2026 Yuichiroh-Kobayashi. 詳細は[LICENSE](LICENSE)を参照してください。
