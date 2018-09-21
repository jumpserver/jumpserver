/**
 * Português translation
 * @author Leandro Carvalho <contato@leandrowebdev.net>
 * @author Wesley Osorio<wesleyfosorio@hotmail.com>
 * @author Fernando H. Bandeira <fernando.bandeira94@gmail.com>
 * @version 2016-04-28
 */
(function(root, factory) {
	if (typeof define === 'function' && define.amd) {
		define(['elfinder'], factory);
	} else if (typeof exports !== 'undefined') {
		module.exports = factory(require('elfinder'));
	} else {
		factory(root.elFinder);
	}
}(this, function(elFinder) {
	elFinder.prototype.i18.pt_BR = {
		translator : 'Leandro Carvalho &lt;contato@leandrowebdev.net&gt;, Wesley Osorio&lt;wesleyfosorio@hotmail.com&gt;, Fernando H. Bandeira &lt;fernando.bandeira94@gmail.com&gt;',
		language   : 'Português',
		direction  : 'ltr',
		dateFormat : 'd M Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Erro',
			'errUnknown'           : 'Erro desconhecido.',
			'errUnknownCmd'        : 'Comando desconhecido.',
			'errJqui'              : 'Configuração inválida do JQuery UI. Verifique se os componentes selectable, draggable e droppable estão incluídos.',
			'errNode'              : 'elFinder requer um elemento DOM para ser criado.',
			'errURL'               : 'Configuração inválida do elFinder! Você deve setar a opção da URL.',
			'errAccess'            : 'Acesso negado.',
			'errConnect'           : 'Incapaz de conectar ao backend.',
			'errAbort'             : 'Conexão abortada.',
			'errTimeout'           : 'Tempo de conexão excedido',
			'errNotFound'          : 'Backend não encontrado.',
			'errResponse'          : 'Resposta inválida do backend.',
			'errConf'              : 'Configuração inválida do backend.',
			'errJSON'              : 'Módulo PHP JSON não está instalado.',
			'errNoVolumes'         : 'Não existe nenhum volume legível disponivel.',
			'errCmdParams'         : 'Parâmetro inválido para o comando "$1".',
			'errDataNotJSON'       : 'Dados não estão no formato JSON.',
			'errDataEmpty'         : 'Dados vazios.',
			'errCmdReq'            : 'Requisição do Backend requer nome de comando.',
			'errOpen'              : 'Incapaz de abrir "$1".',
			'errNotFolder'         : 'Objeto não é uma pasta.',
			'errNotFile'           : 'Objeto não é um arquivo.',
			'errRead'              : 'Incapaz de ler "$1".',
			'errWrite'             : 'Incapaz de escrever em "$1".',
			'errPerm'              : 'Permissão negada.',
			'errLocked'            : '"$1" está bloqueado e não pode ser renomeado, movido ou removido.',
			'errExists'            : 'O nome do arquivo "$1" já existe neste local.',
			'errInvName'           : 'Nome do arquivo inválido.',
			'errFolderNotFound'    : 'Pasta não encontrada.',
			'errFileNotFound'      : 'Arquivo não encontrado.',
			'errTrgFolderNotFound' : 'Pasta de destino "$1" não encontrada.',
			'errPopup'             : 'O seu navegador está bloqueando popup\'s. Para abrir o arquivo, altere esta opção no seu Navegador.',
			'errMkdir'             : 'Incapaz de criar a pasta "$1".',
			'errMkfile'            : 'Incapaz de criar o arquivo "$1".',
			'errRename'            : 'Incapaz de renomear "$1".',
			'errCopyFrom'          : 'Copia dos arquivos do volume "$1" não permitida.',
			'errCopyTo'            : 'Copia dos arquivos para o volume "$1" não permitida.',
			'errMkOutLink'         : 'Incapaz de criar um link fora da unidade raiz.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Erro no upload.',  // old name - errUploadCommon
			'errUploadFile'        : 'Não foi possível fazer o upload "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'Não foi encontrado nenhum arquivo para upload.',
			'errUploadTotalSize'   : 'Os dados excedem o tamanho máximo permitido.', // old name - errMaxSize
			'errUploadFileSize'    : 'Arquivo excede o tamanho máximo permitido.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Tipo de arquivo não permitido.',
			'errUploadTransfer'    : '"$1" erro na transferência.',
			'errUploadTemp'        : 'Incapaz de criar um arquivo temporário para upload.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Objeto "$1" já existe neste local e não pode ser substituído por um objeto com outro tipo.', // new
			'errReplace'           : 'Incapaz de substituir "$1".',
			'errSave'              : 'Incapaz de salvar "$1".',
			'errCopy'              : 'Incapaz de copiar "$1".',
			'errMove'              : 'Incapaz de mover "$1".',
			'errCopyInItself'      : 'Incapaz de copiar "$1" nele mesmo.',
			'errRm'                : 'Incapaz de remover "$1".',
			'errRmSrc'             : 'Incapaz de remover o(s) arquivo(s) fonte.',
			'errExtract'           : 'Incapaz de extrair os arquivos de "$1".',
			'errArchive'           : 'Incapaz de criar o arquivo.',
			'errArcType'           : 'Tipo de arquivo não suportado.',
			'errNoArchive'         : 'Arquivo inválido ou é de um tipo não suportado.',
			'errCmdNoSupport'      : 'Backend não suporta este comando.',
			'errReplByChild'       : 'A pasta “$1” não pode ser substituída por um item que contém.',
			'errArcSymlinks'       : 'Por razões de segurança, negada a permissão para descompactar arquivos que contenham links ou arquivos com nomes não permitidos.', // edited 24.06.2012
			'errArcMaxSize'        : 'Arquivo excede o tamanho máximo permitido.',
			'errResize'            : 'Incapaz de redimensionar "$1".',
			'errResizeDegree'      : 'Grau de rotação inválido.',  // added 7.3.2013
			'errResizeRotate'      : 'Incapaz de rotacionar a imagem.',  // added 7.3.2013
			'errResizeSize'        : 'Tamanho inválido de imagem.',  // added 7.3.2013
			'errResizeNoChange'    : 'Tamanho da imagem não alterado.',  // added 7.3.2013
			'errUsupportType'      : 'Tipo de arquivo não suportado.',
			'errNotUTF8Content'    : 'Arquivo "$1" não está em UTF-8 e não pode ser editado.',  // added 9.11.2011
			'errNetMount'          : 'Incapaz de montar montagem "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Protocolo não suportado.',     // added 17.04.2012
			'errNetMountFailed'    : 'Montagem falhou.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Servidor requerido.', // added 18.04.2012
			'errSessionExpires'    : 'Sua sessão expirou por inatividade.',
			'errCreatingTempDir'   : 'Não foi possível criar um diretório temporário: "$1"',
			'errFtpDownloadFile'   : 'Não foi possível fazer o download do arquivo do FTP: "$1"',
			'errFtpUploadFile'     : 'Não foi possível fazer o upload do arquivo para o FTP: "$1"',
			'errFtpMkdir'          : 'Não foi possível criar um diretório remoto no FTP: "$1"',
			'errArchiveExec'       : 'Erro ao arquivar os arquivos: "$1"',
			'errExtractExec'       : 'Erro na extração dos arquivos: "$1"',
			'errNetUnMount'        : 'Incapaz de desmontar', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Não conversivel para UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Tente utilizar o Google Chrome, se você deseja enviar uma pasta.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Tempo limite atingido para a busca "$1". O resultado da pesquisa é parcial.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Re-autorização é necessária.', // from v2.1.10 added 3.24.2016

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Criar arquivo',
			'cmdback'      : 'Voltar',
			'cmdcopy'      : 'Copiar',
			'cmdcut'       : 'Cortar',
			'cmddownload'  : 'Baixar',
			'cmdduplicate' : 'Duplicar',
			'cmdedit'      : 'Editar arquivo',
			'cmdextract'   : 'Extrair arquivo de ficheiros',
			'cmdforward'   : 'Avançar',
			'cmdgetfile'   : 'Selecionar arquivos',
			'cmdhelp'      : 'Sobre este software',
			'cmdhome'      : 'Home',
			'cmdinfo'      : 'Propriedades',
			'cmdmkdir'     : 'Nova pasta',
			'cmdmkdirin'   : 'Em uma nova pasta', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Novo arquivo',
			'cmdopen'      : 'Abrir',
			'cmdpaste'     : 'Colar',
			'cmdquicklook' : 'Pré-vizualização',
			'cmdreload'    : 'Recarregar',
			'cmdrename'    : 'Renomear',
			'cmdrm'        : 'Deletar',
			'cmdsearch'    : 'Achar arquivos',
			'cmdup'        : 'Ir para o diretório pai',
			'cmdupload'    : 'Fazer upload de arquivo',
			'cmdview'      : 'Vizualizar',
			'cmdresize'    : 'Redimencionar & Rotacionar',
			'cmdsort'      : 'Ordenar',
			'cmdnetmount'  : 'Montar unidade de rede', // added 18.04.2012
			'cmdnetunmount': 'Desmontar', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Para locais', // added 28.12.2014
			'cmdchmod'     : 'Alterar permissão', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Abrir pasta', // from v2.1 added 13.1.2016

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Fechar',
			'btnSave'   : 'Salvar',
			'btnRm'     : 'Remover',
			'btnApply'  : 'Aplicar',
			'btnCancel' : 'Cancelar',
			'btnNo'     : 'Não',
			'btnYes'    : 'Sim',
			'btnMount'  : 'Montar',  // added 18.04.2012
			'btnApprove': 'Vá para $1 & aprove', // from v2.1 added 26.04.2012
			'btnUnmount': 'Desmontar', // from v2.1 added 30.04.2012
			'btnConv'   : 'Converter', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Aqui',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Volume',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Todos',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME Type', // from v2.1 added 22.5.2015
			'btnFileName':'Nome do arquivo',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Salvar & Fechar', // from v2.1 added 12.6.2015
			'btnBackup' : 'Backup', // fromv2.1 added 28.11.2015

			/******************************** notifications ********************************/
			'ntfopen'     : 'Abrir pasta',
			'ntffile'     : 'Abrir arquivo',
			'ntfreload'   : 'Recarregar conteudo da pasta',
			'ntfmkdir'    : 'Criar diretório',
			'ntfmkfile'   : 'Criar arquivos',
			'ntfrm'       : 'Deletar arquivos',
			'ntfcopy'     : 'Copiar arquivos',
			'ntfmove'     : 'Mover arquivos',
			'ntfprepare'  : 'Preparando para copiar arquivos',
			'ntfrename'   : 'Renomear arquivos',
			'ntfupload'   : 'Subindo os arquivos',
			'ntfdownload' : 'Baixando os arquivos',
			'ntfsave'     : 'Salvando os arquivos',
			'ntfarchive'  : 'Criando os arquivos',
			'ntfextract'  : 'Extraindo arquivos compactados',
			'ntfsearch'   : 'Procurando arquivos',
			'ntfresize'   : 'Redimensionando imagens',
			'ntfsmth'     : 'Fazendo alguma coisa',
			'ntfloadimg'  : 'Carregando Imagem',
			'ntfnetmount' : 'Montando unidade de rede', // added 18.04.2012
			'ntfnetunmount': 'Desmontando unidade de rede', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Adquirindo dimensão da imagem', // added 20.05.2013
			'ntfreaddir'  : 'Lendo informações da pasta', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Recebendo URL do link', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Alterando permissões do arquivo', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Verificando o nome do arquivo de upload', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Criando um arquivo para download', // from v2.1.7 added 23.1.2016

			/************************************ dates **********************************/
			'dateUnknown' : 'Desconhecido',
			'Today'       : 'Hoje',
			'Yesterday'   : 'Ontem',
			'msJan'       : 'Jan',
			'msFeb'       : 'Fev',
			'msMar'       : 'Mar',
			'msApr'       : 'Abr',
			'msMay'       : 'Mai',
			'msJun'       : 'Jun',
			'msJul'       : 'Jul',
			'msAug'       : 'Ago',
			'msSep'       : 'Set',
			'msOct'       : 'Out',
			'msNov'       : 'Nov',
			'msDec'       : 'Dez',
			'January'     : 'Janeiro',
			'February'    : 'Fevereiro',
			'March'       : 'Março',
			'April'       : 'Abril',
			'May'         : 'Maio',
			'June'        : 'Junho',
			'July'        : 'Julho',
			'August'      : 'Agosto',
			'September'   : 'Setembro',
			'October'     : 'Outubro',
			'November'    : 'Novembro',
			'December'    : 'Dezembro',
			'Sunday'      : 'Domingo',
			'Monday'      : 'Segunda-feira',
			'Tuesday'     : 'Terça-feira',
			'Wednesday'   : 'Quarta-feira',
			'Thursday'    : 'Quinta-feira',
			'Friday'      : 'Sexta-feira',
			'Saturday'    : 'Sábado',
			'Sun'         : 'Dom',
			'Mon'         : 'Seg',
			'Tue'         : 'Ter',
			'Wed'         : 'Qua',
			'Thu'         : 'Qui',
			'Fri'         : 'Sex',
			'Sat'         : 'Sáb',

			/******************************** sort variants ********************************/
			'sortname'          : 'por nome',
			'sortkind'          : 'por tipo',
			'sortsize'          : 'por tam.',
			'sortdate'          : 'por data',
			'sortFoldersFirst'  : 'Pastas primeiro',

			/********************************** new items **********************************/
			'untitled file.txt' : 'NovoArquivo.txt', // added 10.11.2015
			'untitled folder'   : 'NovaPasta',   // added 10.11.2015
			'Archive'           : 'NovoArquivo',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Confirmação requerida',
			'confirmRm'       : 'Você tem certeza que deseja remover os arquivos?<br />Isto não pode ser desfeito!',
			'confirmRepl'     : 'Substituir arquivo velho com este novo?',
			'confirmConvUTF8' : 'Não está em UTF-8<br/>Converter para UTF-8?<br/>Conteúdo se torna UTF-8 após salvar as conversões.', // from v2.1 added 08.04.2014
			'confirmNotSave'  : 'Isto foi modificado.<br/>Você vai perder seu trabalho caso não salve as mudanças.', // from v2.1 added 15.7.2015
			'apllyAll'        : 'Aplicar a todos',
			'name'            : 'Nome',
			'size'            : 'Tamanho',
			'perms'           : 'Permissões',
			'modify'          : 'Modificado',
			'kind'            : 'Tipo',
			'read'            : 'Ler',
			'write'           : 'Escrever',
			'noaccess'        : 'Inacessível',
			'and'             : 'e',
			'unknown'         : 'Desconhecido',
			'selectall'       : 'Selecionar todos arquivos',
			'selectfiles'     : 'Selecionar arquivo(s)',
			'selectffile'     : 'Selecionar primeiro arquivo',
			'selectlfile'     : 'Slecionar último arquivo',
			'viewlist'        : 'Exibir como lista',
			'viewicons'       : 'Exibir como ícones',
			'places'          : 'Lugares',
			'calc'            : 'Calcular',
			'path'            : 'Caminho',
			'aliasfor'        : 'Alias para',
			'locked'          : 'Bloqueado',
			'dim'             : 'Dimesões',
			'files'           : 'Arquivos',
			'folders'         : 'Pastas',
			'items'           : 'Itens',
			'yes'             : 'sim',
			'no'              : 'não',
			'link'            : 'Link',
			'searcresult'     : 'Resultados da pesquisa',
			'selected'        : 'itens selecionados',
			'about'           : 'Sobre',
			'shortcuts'       : 'Atalhos',
			'help'            : 'Ajuda',
			'webfm'           : 'Gerenciador de arquivos web',
			'ver'             : 'Versão',
			'protocolver'     : 'Versão do protocolo',
			'homepage'        : 'Home do projeto',
			'docs'            : 'Documentação',
			'github'          : 'Fork us on Github',
			'twitter'         : 'Siga-nos no twitter',
			'facebook'        : 'Junte-se a nós no Facebook',
			'team'            : 'Time',
			'chiefdev'        : 'Desenvolvedor chefe',
			'developer'       : 'Desenvolvedor',
			'contributor'     : 'Contribuinte',
			'maintainer'      : 'Mantenedor',
			'translator'      : 'Tradutor',
			'icons'           : 'Ícones',
			'dontforget'      : 'e não se esqueça de levar a sua toalha',
			'shortcutsof'     : 'Atalhos desabilitados',
			'dropFiles'       : 'Solte os arquivos aqui',
			'or'              : 'ou',
			'selectForUpload' : 'Selecione arquivos para upload',
			'moveFiles'       : 'Mover arquivos',
			'copyFiles'       : 'Copiar arquivos',
			'rmFromPlaces'    : 'Remover de Lugares',
			'aspectRatio'     : 'Manter aspecto',
			'scale'           : 'Tamanho',
			'width'           : 'Largura',
			'height'          : 'Altura',
			'resize'          : 'Redimencionar',
			'crop'            : 'Cortar',
			'rotate'          : 'Rotacionar',
			'rotate-cw'       : 'Girar 90 graus CW',
			'rotate-ccw'      : 'Girar 90 graus CCW',
			'degree'          : '°',
			'netMountDialogTitle' : 'Montar Unidade de rede', // added 18.04.2012
			'protocol'            : 'Protocolo', // added 18.04.2012
			'host'                : 'Servidor', // added 18.04.2012
			'port'                : 'Porta', // added 18.04.2012
			'user'                : 'Usuário', // added 18.04.2012
			'pass'                : 'Senha', // added 18.04.2012
			'confirmUnmount'      : 'Deseja desmontar $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Soltar ou colar arquivos do navegador', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Solte ou cole arquivos aqui', // from v2.1 added 07.04.2014
			'encoding'        : 'Codificação', // from v2.1 added 19.12.2014
			'locale'          : 'Local',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Alvo: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Perquisar por input MIME Type', // from v2.1 added 22.5.2015
			'owner'           : 'Dono', // from v2.1 added 20.6.2015
			'group'           : 'Grupo', // from v2.1 added 20.6.2015
			'other'           : 'Outro', // from v2.1 added 20.6.2015
			'execute'         : 'Executar', // from v2.1 added 20.6.2015
			'perm'            : 'Permissão', // from v2.1 added 20.6.2015
			'mode'            : 'Modo', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Pasta vazia', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Pasta vazia\\A Arraste itens para os adicionar', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Pasta vazia\\A De um toque longo para adicionar itens', // from v2.1.6 added 30.12.2015
			'quality'         : 'Qualidade', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Auto sincronização',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Mover para cima',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Obter link', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Itens selecionados ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID da pasta', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Permitir acesso offline', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Se autenticar novamente', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Now loading...', // from v2.1.12 added 4.26.2016

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Desconhecio',
			'kindFolder'      : 'Pasta',
			'kindAlias'       : 'Alias',
			'kindAliasBroken' : 'Alias inválido',
			// applications
			'kindApp'         : 'Aplicação',
			'kindPostscript'  : 'Documento Postscript',
			'kindMsOffice'    : 'Documento Microsoft Office',
			'kindMsWord'      : 'Documento Microsoft Word',
			'kindMsExcel'     : 'Documento Microsoft Excel',
			'kindMsPP'        : 'Apresentação Microsoft Powerpoint',
			'kindOO'          : 'Documento Open Office',
			'kindAppFlash'    : 'Aplicação Flash',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Arquivo Bittorrent',
			'kind7z'          : 'Arquivo 7z',
			'kindTAR'         : 'Arquivo TAR',
			'kindGZIP'        : 'Arquivo GZIP',
			'kindBZIP'        : 'Arquivo BZIP',
			'kindXZ'          : 'Arquivo XZ',
			'kindZIP'         : 'Arquivo ZIP',
			'kindRAR'         : 'Arquivo RAR',
			'kindJAR'         : 'Arquivo JAR',
			'kindTTF'         : 'True Type font',
			'kindOTF'         : 'Open Type font',
			'kindRPM'         : 'Pacote RPM',
			// texts
			'kindText'        : 'Arquivo de texto',
			'kindTextPlain'   : 'Texto simples',
			'kindPHP'         : 'PHP',
			'kindCSS'         : 'CSS',
			'kindHTML'        : 'Documento HTML',
			'kindJS'          : 'Javascript',
			'kindRTF'         : 'Formato Rich Text',
			'kindC'           : 'C',
			'kindCHeader'     : 'C cabeçalho',
			'kindCPP'         : 'C++',
			'kindCPPHeader'   : 'C++ cabeçalho',
			'kindShell'       : 'Unix shell script',
			'kindPython'      : 'Python',
			'kindJava'        : 'Java',
			'kindRuby'        : 'Ruby',
			'kindPerl'        : 'Perl script',
			'kindSQL'         : 'SQL',
			'kindXML'         : 'Documento XML',
			'kindAWK'         : 'AWK',
			'kindCSV'         : 'Valores separados por vírgula',
			'kindDOCBOOK'     : 'Documento Docbook XML',
			'kindMarkdown'    : 'Markdown text', // added 20.7.2015
			// images
			'kindImage'       : 'Imagem',
			'kindBMP'         : 'Imagem BMP',
			'kindJPEG'        : 'Imagem JPEG',
			'kindGIF'         : 'Imagem GIF',
			'kindPNG'         : 'Imagem PNG',
			'kindTIFF'        : 'Imagem TIFF',
			'kindTGA'         : 'Imagem TGA',
			'kindPSD'         : 'Imagem Adobe Photoshop',
			'kindXBITMAP'     : 'Imagem X bitmap',
			'kindPXM'         : 'Imagem Pixelmator',
			// media
			'kindAudio'       : 'Arquivo de audio',
			'kindAudioMPEG'   : 'Audio MPEG',
			'kindAudioMPEG4'  : 'Audio MPEG-4',
			'kindAudioMIDI'   : 'Audio MIDI',
			'kindAudioOGG'    : 'Audio Ogg Vorbis',
			'kindAudioWAV'    : 'Audio WAV',
			'AudioPlaylist'   : 'MP3 playlist',
			'kindVideo'       : 'Arquivo de video',
			'kindVideoDV'     : 'DV filme',
			'kindVideoMPEG'   : 'Video MPEG',
			'kindVideoMPEG4'  : 'Video MPEG-4',
			'kindVideoAVI'    : 'Video AVI',
			'kindVideoMOV'    : 'Quick Time movie',
			'kindVideoWM'     : 'Video Windows Media',
			'kindVideoFlash'  : 'Video Flash',
			'kindVideoMKV'    : 'MKV',
			'kindVideoOGG'    : 'Video Ogg'
		}
	};
}));

