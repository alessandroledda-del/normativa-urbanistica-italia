import sqlite3
from datetime import date
from typing import Optional
from .config import settings

def get_db_connection():
    """Apre connessione al database SQLite."""
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_coefficiente_istat(anno: int) -> float:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT coefficiente FROM coefficienti_istat_oneri WHERE anno = ?",
            (anno,)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return float(row["coefficiente"])
    except Exception:
        pass
    return 1.32  # fallback

def get_tariffe_oneri(
    codice_istat: str,
    destinazione_uso: str,
    tipo_intervento: str,
    zona_urbanistica: Optional[str] = None
) -> Optional[sqlite3.Row]:
    conn = get_db_connection()
    cur = conn.cursor()

    if zona_urbanistica:
        cur.execute("""
            SELECT o.*, c.denominazione AS nome_comune
            FROM oneri_urbanizzazione o
            LEFT JOIN comuni c ON o.codice_istat = c.codice_istat
            WHERE o.codice_istat = ?
              AND o.destinazione_uso = ?
              AND o.tipo_intervento = ?
              AND o.zona_urbanistica = ?
            LIMIT 1
        """, (codice_istat, destinazione_uso, tipo_intervento, zona_urbanistica))
        row = cur.fetchone()
        if row:
            conn.close()
            return row

    cur.execute("""
        SELECT o.*, c.denominazione AS nome_comune
        FROM oneri_urbanizzazione o
        LEFT JOIN comuni c ON o.codice_istat = c.codice_istat
        WHERE o.codice_istat = ?
          AND o.destinazione_uso = ?
          AND o.tipo_intervento = ?
          AND o.zona_urbanistica IS NULL
        LIMIT 1
    """, (codice_istat, destinazione_uso, tipo_intervento))
    row = cur.fetchone()
    conn.close()
    return row

def calcola_oneri(
    codice_istat: str,
    destinazione_uso: str,
    tipo_intervento: str,
    volume_mc: float = 0.0,
    superficie_mq: float = 0.0,
    zona_urbanistica: Optional[str] = None,
    anno_calcolo: Optional[int] = None
) -> str:
    """
    Funzione principale che calcola e restituisce una stringa di testo pronta per l'LLM.
    """
    if anno_calcolo is None:
        anno_calcolo = date.today().year

    tariffa = get_tariffe_oneri(codice_istat, destinazione_uso, tipo_intervento, zona_urbanistica)

    if not tariffa:
        return (f"Tariffe non trovate per: comune {codice_istat}, "
                f"destinazione '{destinazione_uso}', intervento '{tipo_intervento}'.")

    coeff_istat = get_coefficiente_istat(anno_calcolo)
    coeff_rid = float(tariffa["coeff_riduzione"])

    usa_mc = float(tariffa["oneri_primari_mc"]) > 0 or float(tariffa["oneri_secondari_mc"]) > 0

    if usa_mc:
        quantita = volume_mc
        op_unit = float(tariffa["oneri_primari_mc"])
        os_unit = float(tariffa["oneri_secondari_mc"])
        un_misura = "mc"
    else:
        quantita = superficie_mq
        op_unit = float(tariffa["oneri_primari_mq"])
        os_unit = float(tariffa["oneri_secondari_mq"])
        un_misura = "mq"

    oneri_prim = quantita * op_unit * coeff_rid * coeff_istat
    oneri_sec = quantita * os_unit * coeff_rid * coeff_istat
    oneri_tot = oneri_prim + oneri_sec

    cc_mq = float(tariffa["costo_costruzione_mq"])
    perc_cc = float(tariffa["percentuale_cc"])
    mq_cc = superficie_mq if superficie_mq > 0 else (volume_mc * 0.33)
    contributo_cc = mq_cc * cc_mq * perc_cc * coeff_rid

    contributo_totale = oneri_tot + contributo_cc
    nome_comune = tariffa["nome_comune"] if tariffa["nome_comune"] else codice_istat

    out_text = f"Risultati del Calcolo Oneri per il Comune di {nome_comune} (ISTAT {codice_istat}):\n"
    out_text += f"- Oneri Primari: € {round(oneri_prim, 2)}\n"
    out_text += f"- Oneri Secondari: € {round(oneri_sec, 2)}\n"
    out_text += f"Totale Oneri Urbanizzazione: € {round(oneri_tot, 2)}\n\n"
    out_text += f"- Contributo Costo Costruzione (CC): € {round(contributo_cc, 2)}\n"
    out_text += f"-> **ESBORSO COMPLESSIVO STIMATO:** € {round(contributo_totale, 2)}\n\n"
    
    out_text += "Nota per l'agente immobiliare: avverti il cliente che questo conteggio è "
    out_text += f"indicativo e usa le tabelle del {anno_calcolo}. "
    if tariffa["note_normative"]:
        out_text += f"E' presente inoltre la seguente indicazione comunale: {tariffa['note_normative']}."
        
    return out_text
