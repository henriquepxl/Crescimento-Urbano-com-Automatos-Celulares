import os, math
from osgeo import gdal
from copy import deepcopy

# Funcao para ler as camadas (raster) e guardar como uma matriz
def leraster(arquivo):
    fonte = gdal.Open(arquivo)
    banda = fonte.GetRasterBand(1)
    banda = banda.ReadAsArray()
    return (fonte, banda)


def DiferenciaAreaConstruida(img1, img2, urbano=1, tam_pix=30):
    return (sum(sum(((img2 == urbano).astype(int) - (img1 == urbano).astype(int)) != 0)) * (tam_pix ** 2) / 1000000)


# Definindo a classe para ler as imagens classificadas de dois periodos distintos
class classificados():

    def __init__(self, classificado1, classificado2):
        self.fonte_c1, self.matriz_c1 = leraster(classificado1)
        self.fonte_c2, self.matriz_c2 = leraster(classificado2)


class camadas():

    def __init__(self, *args):
        self.c = dict()
        self.cf = dict()
        self.nCmds = len(args)

        n = 1
        for arquivo in args:
            self.cf[n], self.c[n] = leraster(arquivo)
            n += 1

        self.linha = self.cf[1].RasterYSize
        self.coluna = self.cf[1].RasterXSize


class caModel():

    def __init__(self, classifi, camadasModel):
        self.classificacoes = classifi
        self.cmds = camadasModel
        self.tamanho_vizinhanca = 3

        self.linha = self.cmds.linha
        self.coluna = self.cmds.coluna


    def valoresLim(self, Lim_urbano, *Outros_lim):
        self.limite = list(Outros_lim)
        self.Lim_urbano = Lim_urbano


    def previsao(self):
        self.predito = deepcopy(self.classificacoes.matriz_c1)
        margem = math.ceil(self.tamanho_vizinhanca / 2)
        for y in range(margem, self.linha - (margem - 1)):
            for x in range(margem, self.coluna - (margem - 1)):
                vizinhanca = self.classificacoes.matriz_c1[y - (margem - 1):y + (margem),x - (margem - 1):x + (margem)]
                cont_urb = sum(sum(vizinhanca == 1))
                # Se o numero de celulas de urbano for maior do que o limite determinado
                if (cont_urb >= self.Lim_urbano) and (self.cmds.c[5][y, x] != 1):
                    for cam in range(1, self.cmds.nCmds + 1):
                        # Se o valor de limite é menor que zero, então, menor
                        # Se o valor limite é menor que zero, então a regra "menor que" se aplica
                        if self.limite[cam - 1] < 0:
                            if (self.cmds.c[cam][y, x] <= abs(self.limite[cam - 1])):
                                self.predito[y, x] = 1
                            else:
                                pass
                        # Se o valor limite é maior que zero então a regra "maior que" se aplica
                        elif self.limite[cam - 1] > 0:
                            if (self.cmds.c[cam][y, x] >= self.limite[cam - 1]):
                                self.predito[y, x] = 1
                            else:
                                pass

                if (y % 300 == 0) and (x % 300 == 0):
                    print("Linha: %d, Coluna: %d\n" % (y, x), end="\r", flush=True)

    def calcAcuracia(self):
        self.crescimento_verdadeiro = DiferenciaAreaConstruida(self.classificacoes.matriz_c1, self.classificacoes.matriz_c2)
        self.crescimento_previsto = DiferenciaAreaConstruida(self.classificacoes.matriz_c1, self.predito)

        self.acuracia_espacial = 100 - (sum(sum(((self.predito == 1).astype(float) - (self.classificacoes.matriz_c2 == 1).astype(float)) != 0)) / sum(sum(self.classificacoes.matriz_c2 == 1))) * 100

        print("Crescimento Verdadeiro: %d, Crescimento Predito: %d" % (self.crescimento_verdadeiro, self.crescimento_previsto))
        print("Acurácia Espacial: %f" % (self.acuracia_espacial))

    def exportPredito(self, outFileName):
        driver = gdal.GetDriverByName("GTiff")
        outdata = driver.Create(outFileName, self.coluna, self.linha, 1, gdal.GDT_UInt16)  # option: GDT_UInt16, GDT_Float32
        outdata.SetGeoTransform(self.classificacoes.fonte_c1.GetGeoTransform())
        outdata.SetProjection(self.classificacoes.fonte_c1.GetProjection())
        outdata.GetRasterBand(1).WriteArray(self.predito)
        outdata.GetRasterBand(1).SetNoDataValue(0)
        outdata.FlushCache()
        outdata = None

# Identificar o caminho do diretorio onde estão os arquivos
os.chdir("D:\\TCC\\Dados\\teste")

# Entre com as imagens classificadas em GeoTIFF de dois periodos
classificado1 = "classificado2000mb.tif"
classificado2 = "classificado2005mb.tif"

# Entre com todas as camadas
d_centro = "dist_centro.tif"
d_vias = "dist_ruas.tif"
restrito = "restrito.tif"
pop2000= "pop2000.tif"
pop2010 = "pop2010.tif"
decliv = "decliv.tif"

# Cria uma classe que recebe as duas imagens classificadas de dois periodos distintos
imgsClassificadas = classificados(classificado1, classificado2)

camadasUsadas = camadas(d_centro, d_vias, pop2000, decliv, restrito)

# Inicia o modelo com todos os arquivos inseridos acima
rodarCa = caModel(imgsClassificadas, camadasUsadas)

# Coloque os valores limites, coloque valores limites negativos se a regra "menor que" é necessária
# Baseado na estatistica mostrada, os valores limites devem ser ajustados
rodarCa.valoresLim(2, -1, -27000, 8000, -3, -1)

# Roda o modelo
rodarCa.previsao()

# Checa a acurácia dos valores preditos
rodarCa.calcAcuracia()

# Exporta a camada predita
rodarCa.exportPredito('model2019.tif')
