import net.sourceforge.argparse4j.ArgumentParsers
import net.sourceforge.argparse4j.inf.ArgumentParserException
import org.apache.logging.log4j.LogManager
import org.jgroups.*
import java.util.*

/**
 * This Class connects to a cluster, waits for other peers to join and then sends a number of events
 *
 * This implementation uses the SEQUENCER Channel. This uses Total Order and UDP
 *
 * @author Jocelyn Thode
 */
class EventTester(val eventsToSend: Int, val peerNumber: Int, val rate: Long) : ReceiverAdapter() {

    val logger = LogManager.getLogger(this.javaClass)!!

    var channel = JChannel("sequencer.xml")
    val TOTAL_MESSAGES = peerNumber * eventsToSend
    var deliveredMessages = 0

    fun start() {
        channel.receiver = this
        channel.connect("EventCluster")
        logger.info(channel.address.toString())
        logger.info("Peer Number: $peerNumber")

        //Start test when everyone is here
        while (channel.view.size() < peerNumber) {
            Thread.sleep(10)
        }
        runTest()
    }

    private fun runTest() {
        /*
        val randomDelay = Random().nextInt(10) * 1000L
        logger.info("Sleeping for {}ms before sending events", randomDelay)
        Thread.sleep(randomDelay)
        */
        var eventsSent = 0
        logger.info("View size: ${channel.view.size()}")
        logger.info("Sending: $eventsToSend events (rate: 1 every ${rate}ms)")
        while (eventsSent != eventsToSend) {
            Thread.sleep(rate)
            val msg = Message(null, null, "${UUID.randomUUID()}")
            logger.info("Sending: ${msg.`object`}")
            channel.send(msg)
            eventsSent++
        }
        var i = 0
        while (i < 120) {
            logger.debug("Events not yet delivered: {}", (TOTAL_MESSAGES - deliveredMessages))
            Thread.sleep(10000)
            i++
        }
        stop()
    }

    fun stop() {
        channel.disconnect()
        logger.info("Ratio of events delivered: ${deliveredMessages / TOTAL_MESSAGES.toDouble()}")
        logger.info("Messages sent: ${channel.sentMessages}")
        logger.info("Messages received: ${channel.receivedMessages}")
        val stats = channel.dumpStats("UDP", mutableListOf("num_bytes_sent", "num_bytes_received"))["UDP"] as Map<*, *>
        logger.info("Bytes sent: ${stats["num_bytes_sent"]}")
        logger.info("Bytes received: ${stats["num_bytes_received"]}")
        System.exit(0)
    }

    override fun viewAccepted(newView: View) {
        logger.debug("** size: ${newView.size()} ** view: $newView")
    }

    override fun receive(msg: Message) {
        logger.info("Delivered: ${msg.`object`}")
        deliveredMessages++
        if (deliveredMessages >= TOTAL_MESSAGES) {
            logger.info("All events delivered !")
            stop()
        }
    }
}

fun main(args: Array<String>) {
    val parser = ArgumentParsers.newArgumentParser("EpTO tester")
    parser.defaultHelp(true)
    parser.addArgument("peerNumber").help("Peer number")
            .type(Integer.TYPE)
            .setDefault(35)
    parser.addArgument("-e", "--events").help("Number of events to send")
            .type(Integer.TYPE)
            .setDefault(12)
    parser.addArgument("-r", "--rate").help("Time between each event broadcast in ms")
            .type(Long::class.java)
            .setDefault(1000L)

    try {
        val res = parser.parseArgs(args)
        val eventTester = EventTester(res.getInt("events"), res.getInt("peerNumber"), res.getLong("rate"))
        eventTester.start()
        while (true) Thread.sleep(500)
    } catch (e: ArgumentParserException) {
        parser.handleError(e)
    }
}
