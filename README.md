# Wingman Platform Reader

```shell
docker run -it --rm -p 8000:8000 ghcr.io/adrianliechti/wingman-reader
```

### Examples

#### PDF

```shell
curl -L -H "X-Return-Format:pdf" http://localhost:8000/https://www.example.org
```


#### HTML

```shell
curl -L -H "X-Return-Format:html" http://localhost:8000/https://www.example.org
```

#### Plain Text

```shell
curl -L -H "X-Return-Format:text" http://localhost:8000/https://www.example.org
```

#### Markdown

```shell
curl -L -H "X-Return-Format:markdown" http://localhost:8000/https://www.example.org
```
