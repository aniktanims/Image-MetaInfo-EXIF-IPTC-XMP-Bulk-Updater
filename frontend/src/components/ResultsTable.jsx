import { FiList } from "react-icons/fi";

export default function ResultsTable({ results }) {
  if (!results.length) {
    return null;
  }

  const displayPath = (path) => {
    if (!path) {
      return "-";
    }
    return path.replace(/^[A-Za-z]:\\/, "").replace(/\\/g, " > ");
  };

  return (
    <section className="panel">
      <h2 className="title-with-icon"><FiList /> Results</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Output</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {results.map((item, index) => (
              <tr key={`${item.file_path}-${index}`}>
                <td>{displayPath(item.file_path)}</td>
                <td>
                  <span className={`badge badge-${item.status}`}>{item.status}</span>
                </td>
                <td>{displayPath(item.output_path)}</td>
                <td>{item.error ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
