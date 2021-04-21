import alpaca_trade_api as tradeapi
from typing import Dict, List
import os
import pathlib as p
import pandas as pd
from datetime import datetime, timedelta
from models.settings import Settings


class AlpacaData:
    def __init__(self, paper=True):
        """
        I don't think there's any different in the data quality between paper and live accounts.
        200 api calls/ min
        """
        key_names = Settings.keys_names
        base_url = "https://data.alpaca.markets"
        if paper:
            key_id = key_names["Alpaca Paper Key ID"]
            secret_key = key_names["Alpaca Paper Secret Key"]
        else:
            key_id = key_names["Alpaca Live Key ID"]
            secret_key = key_names["Alpaca Live Secret Key"]

        key_id = os.environ[key_id]
        secret_key = os.environ[secret_key]

        self.api = tradeapi.REST(key_id, secret_key, base_url=base_url)
        del key_id, secret_key

    def get_bars_data(self, tickers: list, timeframe: str = 'day',
                      start: datetime = datetime.now() - timedelta(days=31), end: datetime = datetime.now(),
                      limit=1000, print_out=True) -> Dict[str, pd.DataFrame]:

        if isinstance(tickers, str):
            tickers = [tickers]

        if limit == 0:
            d = dict()
            for t in tickers:
                d[t] = pd.DataFrame()
            return d

        assert timeframe in {"minute", "1Min", "5Min", "15Min", "day"}  # minute == 1Min

        assert isinstance(tickers, list)

        start = start.isoformat()
        end = end.isoformat()

        data = {}
        for ticker in tickers:
            if print_out:
                print(f"Getting bars data for {ticker} from {start} to {end} ...")
            response = self.api.get_barset(ticker, timeframe, limit, start, end)
            df = pd.DataFrame(columns=['close', 'open', 'high', 'low', 'volume', 'time'])
            for bar in response[ticker]:
                t = datetime.fromtimestamp(bar._raw['t'])
                df = df.append({'close': bar._raw['c'],
                                'open': bar._raw['o'],
                                'high': bar._raw['h'],
                                'low': bar._raw['l'],
                                'volume': bar._raw['v'],
                                'time': t.isoformat()},
                               ignore_index=True)
            data[ticker] = df

        return data

    def get_api(self):
        return self.api

    def download_bars_data(self, download_path: str, symbols: List[str], timespan: int, replace_old_data=False) -> None:
        # check to see if data exists
        # if files are there
            # open files with pandas, append to them if necessary. Maybe open both new and old data in pands,
            # concatonate the two and let pandas sort out the time stamps
        # else no data or replace_old_data
            #
        dir = p.Path(download_path)
        if not dir.is_dir():
            raise ValueError(f"the given download path doesn't exists\n{download_path}"
                             f"\nPlease make this directory and try again")
        now = datetime.today()
        begin = now - timedelta(timespan)
        for i in range(len(symbols)):
            sym = symbols[i]
            sym = sym.upper()
            f = dir.joinpath(f"{sym}.csv")
            if f.exists() and not replace_old_data:
                print(f"({i+1} of {len(symbols)}) Appending to existing data {sym} found")
                df = pd.read_csv(str(f))
                df = df.sort_values(by='time', ascending=False)
                df = df.reset_index(drop=True)
                # TODO check if it satisfies the begin and end bounds, else get bars data
                days_off_current = (now - datetime.fromisoformat(df['time'][0])).days
                if days_off_current < 0:
                    days_off_current = 0
                days_off_past = (datetime.fromisoformat(df['time'].iloc[-1]) - begin).days
                if days_off_past < 0:
                    days_off_past = 0
                e_data = self.get_bars_data([sym], 'day', start=begin, end=now, limit=days_off_current, print_out=False)
                s_data = self.get_bars_data([sym], 'day', start=begin, end=datetime.fromisoformat(df['time'].iloc[-1]),
                                              limit=days_off_past, print_out=False)
                df = df.append(e_data[sym])
                df = df.append(s_data[sym])
                df = df.drop_duplicates(subset=['time'])
                df = df.sort_values(by='time', ascending=False)
                df = df.reset_index(drop=True)
                df.to_csv(str(f), index=False)
            else:
                print(f"({i+1} of {len(symbols)}) Finding data for {sym}")
                # Limit is the driving factor over start and end. So to reduce time, were estimating the number of
                # trading days between start and end with 5 of the 7 days of the week
                data = self.get_bars_data([sym], 'day', start=begin, end=now, limit=timespan*5//7, print_out=False)
                data[sym].to_csv(str(f), index=False)






