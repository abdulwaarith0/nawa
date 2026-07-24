"use client";

import { type ReactNode, useMemo } from "react";
import "./styles.css";

export interface TableColumn<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  align?: "start" | "end";
}

export interface IProps<T> {
  columns: TableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: ReactNode;
}

// .nw-table — generic sortable-by-the-API rows table (§9). The API already
// returns rank-ordered/filtered rows (canon: filters live server-side), so
// this component only renders — it never re-sorts or re-filters client-side.
export default function Table<T>({
  columns,
  rows,
  getRowKey,
  onRowClick,
  emptyMessage,
}: IProps<T>) {
  return useMemo(() => {
    if (rows.length === 0) {
      return <div className="nw-table-empty">{emptyMessage}</div>;
    }
    return (
      <div className="nw-table-scroll">
        <table className="nw-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} data-align={col.align ?? "start"}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const key = getRowKey(row);
              return (
                <tr
                  key={key}
                  className={onRowClick ? "nw-table-row-clickable" : undefined}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  onKeyDown={
                    onRowClick
                      ? (event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onRowClick(row);
                          }
                        }
                      : undefined
                  }
                  tabIndex={onRowClick ? 0 : undefined}
                  role={onRowClick ? "button" : undefined}
                >
                  {columns.map((col) => (
                    <td key={col.key} data-align={col.align ?? "start"}>
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }, [columns, rows, getRowKey, onRowClick, emptyMessage]);
}
