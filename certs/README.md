# Russian Trusted Root CA

`russian_trusted_root_ca.pem` — корневой сертификат Минцифры России, которым подписан
сертификат T-Invest API (`invest-public-api.tbank.ru`).

* Источник: https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt (Госуслуги).
* SHA-256: `D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`
  — совпадает с корнем в цепочке сервера API и с сертификатом в исходниках SDK `t-tech-investments`.
* Действует до 27.02.2032.

Сертификат **не устанавливается в Windows**: им пользуется только gRPC-клиент этого
приложения (переменная `GRPC_DEFAULT_SSL_ROOTS_FILE_PATH`, см. `config/settings.py`).
Проверка TLS не отключается. То же делает официальный SDK с `SSL_TBANK_VERIFY=True`.
