import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

// Renders the financial graph as a D3 force-directed map. Node colour/size and
// edge width come straight from the API payload (computed server-side).
export default function MindMap({ graph }) {
  const svgRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!graph || !svgRef.current) return

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight

    // d3 mutates node/link objects, so work on copies.
    const nodes = graph.nodes.map((n) => ({ ...n }))
    const links = graph.edges.map((e) => ({ ...e }))

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('viewBox', [0, 0, width, height])

    const root = svg.append('g')

    const zoom = d3
      .zoom()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => root.attr('transform', event.transform))
    svg.call(zoom)

    const link = root
      .append('g')
      .attr('stroke', '#3b4453')
      .attr('stroke-opacity', 0.7)
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', (d) => d.width || 1)

    const node = root
      .append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .call(drag())

    node
      .append('circle')
      .attr('r', (d) => (d.size || 20) / 2)
      .attr('fill', (d) => d.color || '#9b9b9b')
      .attr('stroke', '#0d1117')
      .attr('stroke-width', 1.5)

    node
      .append('text')
      .text((d) => d.label)
      .attr('x', (d) => (d.size || 20) / 2 + 4)
      .attr('y', 4)
      .attr('fill', '#c9d1d9')
      .attr('font-size', 11)

    node.append('title').text((d) =>
      d.amount ? `${d.label}: $${Number(d.amount).toLocaleString()}` : d.label,
    )

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        'link',
        d3.forceLink(links).id((d) => d.id).distance(90).strength(0.4),
      )
      .force('charge', d3.forceManyBody().strength(-280))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force(
        'collide',
        d3.forceCollide().radius((d) => (d.size || 20) / 2 + 6),
      )

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)
      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })

    function drag() {
      return d3
        .drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        })
    }

    return () => simulation.stop()
  }, [graph])

  return (
    <div className="mindmap" ref={containerRef}>
      <svg ref={svgRef} width="100%" height="100%" />
    </div>
  )
}
