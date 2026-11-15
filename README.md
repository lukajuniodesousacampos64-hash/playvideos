# Play Vídeos

Painel que gera vídeos MP4 (com áudio) usando o GitHub Actions.

## Passo a passo
1. Crie um repositório **público** no GitHub (o GitHub Pages grátis exige repositório público) e suba todos os arquivos desta pasta, na branch `main`.
2. **Settings → Pages**: Source = *Deploy from a branch*, branch `main`, pasta `/docs`.
3. **Settings → Actions → General → Workflow permissions**: marque *Read and write permissions*.
4. (Opcional, roteiro automático pela IA) **Settings → Secrets and variables → Actions**: crie o secret `ANTHROPIC_API_KEY`. Sem ele, o vídeo usa o próprio texto do pedido como narração.
5. Crie um token em **GitHub → Settings → Developer settings → Fine-grained tokens**, só para este repositório, com permissão **Actions: Read and write**.
6. Na Cloudflare, crie um Worker (grátis) com o conteúdo de `worker/worker.js` e estas variáveis (as duas secretas como *Secret*):
   - `GH_TOKEN` (secret): o token do passo 5
   - `APP_KEY` (secret): uma senha que você inventa
   - `GH_REPO`: `seu-usuario/nome-do-repo`
   - `ALLOWED_ORIGIN`: `https://seu-usuario.github.io`
7. Em `docs/config.js`, cole a URL do Worker em `WORKER_URL` e faça commit.
8. Abra `https://seu-usuario.github.io/nome-do-repo/`, peça um vídeo e digite a senha (`APP_KEY`) quando o app pedir. O vídeo aparece na lista em poucos minutos.

## Observações
- O modelo 3D usa por enquanto a cena do roteador Wi-Fi com a narração do seu tema. O 3D completo da skill Remotion entra numa próxima etapa.
- Teste local: `python gerar.py --id teste --modelo dinamico --tema "Seu tema aqui"` (precisa de ffmpeg, espeak-ng, pillow e numpy).
