import Table, { type TableColumn } from "@/components/Table";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

interface Row {
  id: string;
  name: string;
  score: number;
}

const columns: TableColumn<Row>[] = [
  { key: "name", header: "Name", render: (row) => row.name },
  { key: "score", header: "Score", render: (row) => row.score, align: "end" },
];

describe("Table", () => {
  it("renders headers and one row per item", () => {
    render(
      <Table
        columns={columns}
        rows={[
          { id: "1", name: "Amina", score: 80 },
          { id: "2", name: "Yusuf", score: 60 },
        ]}
        getRowKey={(row) => row.id}
      />,
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Amina")).toBeInTheDocument();
    expect(screen.getByText("Yusuf")).toBeInTheDocument();
  });

  it("renders the empty message when there are no rows", () => {
    render(
      <Table columns={columns} rows={[]} getRowKey={(row) => row.id} emptyMessage="Nothing here" />,
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("calls onRowClick when a row is clicked", async () => {
    const onRowClick = vi.fn();
    render(
      <Table
        columns={columns}
        rows={[{ id: "1", name: "Amina", score: 80 }]}
        getRowKey={(row) => row.id}
        onRowClick={onRowClick}
      />,
    );
    await userEvent.click(screen.getByText("Amina"));
    expect(onRowClick).toHaveBeenCalledWith({ id: "1", name: "Amina", score: 80 });
  });

  it("activates onRowClick via Enter and Space when the row has focus", async () => {
    const onRowClick = vi.fn();
    render(
      <Table
        columns={columns}
        rows={[{ id: "1", name: "Amina", score: 80 }]}
        getRowKey={(row) => row.id}
        onRowClick={onRowClick}
      />,
    );
    const row = screen.getByRole("button");
    row.focus();
    await userEvent.keyboard("{Enter}");
    expect(onRowClick).toHaveBeenCalledTimes(1);
    await userEvent.keyboard(" ");
    expect(onRowClick).toHaveBeenCalledTimes(2);
  });

  it("does not make rows focusable/clickable when onRowClick is absent", () => {
    render(
      <Table
        columns={columns}
        rows={[{ id: "1", name: "Amina", score: 80 }]}
        getRowKey={(row) => row.id}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
