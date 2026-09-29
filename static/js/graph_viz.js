/* static/js/graph_viz.js — D3.js Stock Correlation Graph & Travel Algorithms */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const container = document.getElementById('graph-container');
  const selectAlgo = document.getElementById('select-algo');
  const startContainer = document.getElementById('param-start-container');
  const endContainer = document.getElementById('param-end-container');
  const btnRun = document.getElementById('btn-run-algo');
  const btnClear = document.getElementById('btn-clear-highlight');
  const btnZoom = document.getElementById('btn-zoom-fit');
  const btnRebuild = document.getElementById('btn-rebuild-graph');
  const tooltip = document.getElementById('tooltip');
  const outputConsole = document.getElementById('algo-output');
  const descConsole = document.getElementById('algo-description');

  if (!container) return;

  // D3 Variables
  let svg, gContainer, simulation;
  let d3Nodes, d3Links, d3Labels;
  let graphData = null;
  let zoomBehavior;

  // Track state
  const width = container.clientWidth || 700;
  const height = container.clientHeight || 500;

  // Initialise Page
  setupAlgoParams();
  loadGraph();

  // Listeners
  selectAlgo.addEventListener('change', setupAlgoParams);
  btnRun.addEventListener('click', runAlgorithm);
  btnClear.addEventListener('click', clearHighlights);
  btnZoom.addEventListener('click', zoomFit);
  btnRebuild.addEventListener('click', rebuildGraph);

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Algo Form Settings
  // ──────────────────────────────────────────────────────────────────────────
  function setupAlgoParams() {
    const val = selectAlgo.value;
    if (val === 'bfs' || val === 'dfs') {
      startContainer.classList.remove('d-none');
      endContainer.classList.add('d-none');
    } else if (val === 'dijkstra') {
      startContainer.classList.remove('d-none');
      endContainer.classList.remove('d-none');
    } else {
      startContainer.classList.add('d-none');
      endContainer.classList.add('d-none');
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Load Graph Data & Draw D3 Graph
  // ──────────────────────────────────────────────────────────────────────────
  async function loadGraph() {
    container.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
      const res = await fetch('/api/graph-data');
      graphData = await res.json();
      container.innerHTML = ''; // Clear spinner

      if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
        container.innerHTML = '<div class="text-center py-5 text-muted">No stock correlation graph available. Visit Admin Panel to rebuild graph.</div>';
        return;
      }

      // Update metrics UI
      document.getElementById('val-nodes').innerText = graphData.stats.node_count;
      document.getElementById('val-edges').innerText = graphData.stats.edge_count;
      document.getElementById('val-density').innerText = graphData.stats.density;

      // Draw svg
      drawD3Graph(graphData);

    } catch (err) {
      console.error('Error loading graph:', err);
      container.innerHTML = '<div class="text-center py-5 text-danger">Error fetching graph data.</div>';
    }
  }

  function drawD3Graph(data) {
    const nodes = data.nodes;
    const links = data.links;

    // Create SVG
    svg = d3.select('#graph-container')
      .append('svg')
      .attr('id', 'graph-canvas')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('width', '100%')
      .attr('height', '100%');

    // Create Zoom G wrapper
    gContainer = svg.append('g').attr('class', 'graph-g');

    // Zoom Behaviour
    zoomBehavior = d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => {
        gContainer.attr('transform', event.transform);
      });
    svg.call(zoomBehavior);

    // Simulation forces
    simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(130))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => d.size + 15));

    // Draw Links
    d3Links = gContainer.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('class', d => `link ${d.correlation >= 0 ? 'positive' : 'negative'}`)
      .attr('stroke-width', d => 1.5 + Math.abs(d.correlation) * 4)
      .on('mouseover', showLinkTooltip)
      .on('mousemove', moveTooltip)
      .on('mouseout', hideTooltip);

    // Draw Nodes (Groups)
    d3Nodes = gContainer.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended)
      );

    // Draw Circle
    d3Nodes.append('circle')
      .attr('class', 'node')
      .attr('r', d => d.size)
      .attr('fill', d => d.color || '#00d4ff')
      .on('mouseover', showNodeTooltip)
      .on('mousemove', moveTooltip)
      .on('mouseout', hideTooltip)
      .on('click', (e, d) => selectNodeInParams(d.id));

    // Draw Label
    d3Labels = d3Nodes.append('text')
      .attr('class', 'node-label')
      .attr('dx', 0)
      .attr('dy', '.31em')
      .attr('text-anchor', 'middle')
      .text(d => d.id);

    // Simulation Tick
    simulation.on('tick', () => {
      d3Links
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      d3Nodes
        .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Zoom to fit initial
    setTimeout(zoomFit, 100);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Drag Behaviors
  // ──────────────────────────────────────────────────────────────────────────
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Tooltips
  // ──────────────────────────────────────────────────────────────────────────
  function showNodeTooltip(event, d) {
    tooltip.classList.remove('d-none');
    tooltip.innerHTML = `
      <div class="fw-bold fs-7 text-info">${d.id}</div>
      <div class="text-white">${d.name}</div>
      <div class="text-muted mt-1">Sector: ${d.sector}</div>
      <div class="text-cyan mt-1">PageRank: ${d.pagerank.toFixed(5)}</div>
      <div class="text-muted fs-8 mt-1">Click node to select in controls</div>
    `;
  }

  function showLinkTooltip(event, d) {
    tooltip.classList.remove('d-none');
    const u = d.source.id || d.source;
    const v = d.target.id || d.target;
    tooltip.innerHTML = `
      <div class="fw-bold fs-7 text-warning">${u} &harr; ${v}</div>
      <div class="text-white">Correlation: ${d.correlation.toFixed(4)}</div>
      <div class="text-muted mt-1">Type: ${d.edge_type}</div>
    `;
  }

  function moveTooltip(event) {
    const containerRect = container.getBoundingClientRect();
    const tooltipWidth = tooltip.offsetWidth;
    const tooltipHeight = tooltip.offsetHeight;
    
    let x = event.clientX - containerRect.left + 15;
    let y = event.clientY - containerRect.top + 15;

    // Boundary checks
    if (x + tooltipWidth > containerRect.width) x = event.clientX - containerRect.left - tooltipWidth - 10;
    if (y + tooltipHeight > containerRect.height) y = event.clientY - containerRect.top - tooltipHeight - 10;

    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
  }

  function hideTooltip() {
    tooltip.classList.add('d-none');
  }

  // Click handler to select node in parameter selects
  function selectNodeInParams(tickerId) {
    const startSelect = document.getElementById('select-start');
    const endSelect = document.getElementById('select-end');
    
    // Fill active parameter selector
    if (!startContainer.classList.contains('d-none') && !endContainer.classList.contains('d-none')) {
      // Dijkstra is selected; fill end if start is already set, or alternate
      if (startSelect.value === tickerId) {
        // Toggle
      } else {
        endSelect.value = tickerId;
      }
    } else if (!startContainer.classList.contains('d-none')) {
      startSelect.value = tickerId;
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Zoom Fit
  // ──────────────────────────────────────────────────────────────────────────
  function zoomFit() {
    if (!svg || !gContainer || !graphData) return;
    
    const nodes = graphData.nodes;
    if (nodes.length === 0) return;

    let minX = d3.min(nodes, d => d.x);
    let maxX = d3.max(nodes, d => d.x);
    let minY = d3.min(nodes, d => d.y);
    let maxY = d3.max(nodes, d => d.y);

    const graphW = maxX - minX || 1;
    const graphH = maxY - minY || 1;
    const midX = (minX + maxX) / 2;
    const midY = (minY + maxY) / 2;

    const scale = 0.85 / Math.max(graphW / width, graphH / height);
    const transform = d3.zoomIdentity
      .translate(width / 2 - scale * midX, height / 2 - scale * midY)
      .scale(Math.min(Math.max(scale, 0.4), 1.8));

    svg.transition().duration(750).call(zoomBehavior.transform, transform);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Algorithm Calculation Handler
  // ──────────────────────────────────────────────────────────────────────────
  async function runAlgorithm() {
    const algo = selectAlgo.value;
    const start = document.getElementById('select-start').value;
    const end = document.getElementById('select-end').value;

    outputConsole.innerText = '[Computing] Fetching results ...';
    clearHighlights();

    try {
      const res = await fetch(`/api/graph-algorithm/${algo}?start=${start}&end=${end}`);
      const data = await res.json();

      if (!data.success) {
        outputConsole.innerText = `[Error] ${data.error || 'Computation failed'}`;
        return;
      }

      const result = data.result;
      
      // Update description console
      descConsole.innerText = result.description || 'Calculation completed.';

      // Display formatted results on output console
      displayAlgoOutput(algo, result);

      // Highlight nodes & edges in the D3 graph
      highlightAlgoResult(algo, result);

    } catch (err) {
      console.error('Algo run error:', err);
      outputConsole.innerText = `[Error] Failed to connect to backend calculations.`;
    }
  }

  function displayAlgoOutput(algo, result) {
    if (algo === 'bfs' || algo === 'dfs') {
      let orderStr = result.order.map((o, i) => `${i+1}. ${o.node} (${o.name})`).join('\n');
      outputConsole.innerHTML = `Traversal Sequence:\n${orderStr}`;
    } 
    else if (algo === 'dijkstra') {
      if (result.error) {
        outputConsole.innerHTML = `No Path Found:\n${result.error}`;
        return;
      }
      let pathStr = result.path.map((p, i) => {
        if (i === 0) return `${p.node}`;
        return ` &rarr; ${p.node} (corr: ${p.correlation})`;
      }).join('\n');
      outputConsole.innerHTML = `Shortest Path (Strongest Influence):\n${pathStr}\n\nTotal Correlation Cost Weight: ${result.total_distance}`;
    } 
    else if (algo === 'pagerank') {
      let scoreStr = result.scores.map(s => `#${s.rank} ${s.node}: ${s.score.toFixed(6)} (${s.score_pct}%)`).join('\n');
      outputConsole.innerHTML = `PageRank Node Influence Ratings:\n${scoreStr}`;
    } 
    else if (algo === 'mst') {
      let edgeStr = result.edges.map(e => `${e.source} &harr; ${e.target} (corr: ${e.correlation})`).join('\n');
      outputConsole.innerHTML = `Minimum Spanning Tree (Strongest Backbone):\n${edgeStr}\n\nTotal Edges Kept: ${result.edge_count}`;
    }
  }

  function highlightAlgoResult(algo, result) {
    // Collect nodes & edges to highlight
    const nodesToHighlight = new Set();
    const edgesToHighlight = new Set(); // set of string format "u-v"

    if (algo === 'bfs' || algo === 'dfs') {
      result.order.forEach(o => nodesToHighlight.add(o.node));
      result.edges.forEach(e => {
        edgesToHighlight.add(`${e.source}-${e.target}`);
        edgesToHighlight.add(`${e.target}-${e.source}`);
      });
    } 
    else if (algo === 'dijkstra') {
      if (result.path_nodes) {
        result.path_nodes.forEach(n => nodesToHighlight.add(n));
        for (let i = 0; i < result.path_nodes.length - 1; i++) {
          const u = result.path_nodes[i];
          const v = result.path_nodes[i+1];
          edgesToHighlight.add(`${u}-${v}`);
          edgesToHighlight.add(`${v}-${u}`);
        }
      }
    } 
    else if (algo === 'pagerank') {
      // Highlight the top 3 nodes
      if (result.scores && result.scores.length > 0) {
        nodesToHighlight.add(result.scores[0].node);
        nodesToHighlight.add(result.scores[1].node);
        nodesToHighlight.add(result.scores[2].node);
      }
    } 
    else if (algo === 'mst') {
      if (result.nodes) result.nodes.forEach(n => nodesToHighlight.add(n.node));
      if (result.edges) {
        result.edges.forEach(e => {
          edgesToHighlight.add(`${e.source}-${e.target}`);
          edgesToHighlight.add(`${e.target}-${e.source}`);
        });
      }
    }

    if (nodesToHighlight.size === 0) return;

    // Apply classes
    d3Nodes.selectAll('circle').each(function(d) {
      const self = d3.select(this);
      if (nodesToHighlight.has(d.id)) {
        self.classed('highlighted', true).classed('faded', false);
      } else {
        self.classed('faded', true).classed('highlighted', false);
      }
    });

    d3Links.each(function(d) {
      const self = d3.select(this);
      const u = d.source.id || d.source;
      const v = d.target.id || d.target;
      const key = `${u}-${v}`;
      if (edgesToHighlight.has(key)) {
        self.classed('highlighted', true).classed('faded', false);
      } else {
        self.classed('faded', true).classed('highlighted', false);
      }
    });
  }

  function clearHighlights() {
    if (!d3Nodes || !d3Links) return;
    d3Nodes.selectAll('circle').classed('faded', false).classed('highlighted', false);
    d3Links.classed('faded', false).classed('highlighted', false);
    outputConsole.innerHTML = '[Ready] Waiting for algorithm execution...';
    descConsole.innerText = 'Select an algorithm and click Compute to run graph calculations.';
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Rebuild Graph Trigger
  // ──────────────────────────────────────────────────────────────────────────
  async function rebuildGraph() {
    btnRebuild.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Rebuilding...';
    btnRebuild.disabled = true;

    try {
      const res = await fetch('/api/rebuild-graph', { method: 'POST' });
      const data = await res.json();
      
      btnRebuild.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i> Rebuild Graph';
      btnRebuild.disabled = false;

      if (data.success) {
        loadGraph();
      } else {
        alert(`Failed to rebuild graph: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      btnRebuild.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i> Rebuild Graph';
      btnRebuild.disabled = false;
      alert('Network error trying to rebuild correlation graph.');
    }
  }
});
